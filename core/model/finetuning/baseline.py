# -*- coding: utf-8 -*-
"""
@inproceedings{DBLP:conf/iclr/ChenLKWH19,
  author    = {Wei{-}Yu Chen and
               Yen{-}Cheng Liu and
               Zsolt Kira and
               Yu{-}Chiang Frank Wang and
               Jia{-}Bin Huang},
  title     = {A Closer Look at Few-shot Classification},
  booktitle = {7th International Conference on Learning Representations, {ICLR} 2019,
               New Orleans, LA, USA, May 6-9, 2019},
  year      = {2019},
  url       = {https://openreview.net/forum?id=HkxLXnAcFQ}
}
https://arxiv.org/abs/1904.04232

Adapted from https://github.com/wyharveychen/CloserLookFewShot.
"""
import pdb
import torch
from torch import nn

from core.utils import accuracy
from .finetuning_model import FinetuningModel


class Baseline(FinetuningModel):
    def __init__(self, feat_dim, num_class, inner_param, **kwargs):
        super(Baseline, self).__init__(**kwargs)
        self.feat_dim = feat_dim
        self.num_class = num_class
        self.inner_param = inner_param

        self.classifier = nn.Linear(self.feat_dim, self.num_class)
        self.loss_func = nn.CrossEntropyLoss()

    def set_forward(self, batch):
        """
        :param batch:
        :return:
        """
        image, global_target = batch
        image = image.to(self.device)
        with torch.no_grad():
            feat = self.emb_func(image)

        support_feat, query_feat, support_target, query_target = self.split_by_episode(
            feat, mode=1
        )
        episode_size = support_feat.size(0)

        output_list = []
        for i in range(episode_size):
            output = self.set_forward_adaptation(
                support_feat[i], support_target[i], query_feat[i]
            )
            output_list.append(output)

        output = torch.cat(output_list, dim=0)
        acc = accuracy(output, query_target.reshape(-1))

        return output, acc

    def set_forward_loss(self, batch):
        """
        :param batch:
        :return:
        """
        image, target = batch
        image = image.to(self.device)
        target = target.to(self.device)

        feat = self.emb_func(image)
        output = self.classifier(feat)
        loss = self.loss_func(output, target)
        acc = accuracy(output, target)
        return output, acc, loss

    def set_forward_adaptation(self, support_feat, support_target, query_feat):
        classifier = nn.Linear(self.feat_dim, self.way_num)
        optimizer = self.sub_optimizer(classifier, self.inner_param["inner_optim"])

        classifier = classifier.to(self.device)

        classifier.train()
        support_size = support_feat.size(0)
        for epoch in range(self.inner_param["inner_train_iter"]):
            rand_id = torch.randperm(support_size)
            for i in range(0, support_size, self.inner_param["inner_batch_size"]):
                select_id = rand_id[
                    i : min(i + self.inner_param["inner_batch_size"], support_size)
                ]
                batch = support_feat[select_id]
                target = support_target[select_id]

                output = classifier(batch)

                loss = self.loss_func(output, target)

                optimizer.zero_grad()
                loss.backward(retain_graph=True)
                optimizer.step()

        output = classifier(query_feat)
        return output
