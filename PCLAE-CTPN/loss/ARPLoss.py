import torch
import torch.nn as nn
import torch.nn.functional as F
from loss.Dist import Dist

class ARPLoss(nn.CrossEntropyLoss):
    def __init__(self, **options):
        super(ARPLoss, self).__init__()
        self.use_gpu = options['use_gpu']
        self.weight_pl = float(options['weight_pl'])
        self.temp = options['temp']
        self.num_classes = options['num_classes']
        self.num_centers = options['num_centers']
        self.Dist = Dist(num_classes=options['num_classes'], num_centers = options['num_centers'], feat_dim=options['feat_dim'])
        self.center_points = self.Dist.centers
        self.radius = nn.Parameter(torch.Tensor(1))
        self.radius.data.fill_(0)
        self.margin_loss = nn.MarginRankingLoss(margin=1.0)


    def forward(self, x, y, labels=None):
        dist_dot_p = self.Dist(x, center=self.center_points, metric='dot')
        dist_l2_p = self.Dist(x, center=self.center_points)
        logits = -(dist_l2_p - dist_dot_p)

        if labels is None: return logits, 0
        loss = F.cross_entropy(logits / self.temp, labels.long())

        unique_labels = torch.unique(labels)
        loss_r_list = []

        for label in unique_labels:
            mask = (labels == label)
            x_class = x[mask]
            label_class = labels[mask]
            center_class = self.center_points[label_class, :]
            _dis_known = (x_class - center_class).pow(2).mean(1)  # formula (12)
            target = torch.ones(_dis_known.size()).cuda()
            loss_r = self.margin_loss(self.radius, _dis_known, target)
            loss_r_list.append(loss_r)

        loss_r_total = torch.mean(torch.stack(loss_r_list))
        loss = loss + self.weight_pl * loss_r_total

        return logits, loss, loss_r_total

    def fake_loss(self, x):
        logits = self.Dist(x, center=self.points)
        prob = F.softmax(logits, dim=1)
        loss = (prob * torch.log(prob)).sum(1).mean().exp()

        return loss
