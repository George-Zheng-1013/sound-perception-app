import librosa
import numpy as np
import torch
from utils import AverageMeter


def train(net, criterion, optimizer, trainloader, epoch=None, clap_model=None, **options):
    net.train()
    losses = AverageMeter()
    loss_o_meter = AverageMeter()

    torch.cuda.empty_cache()
    loss_all = 0
    for batch_idx, (paths, data, labels) in enumerate(trainloader):
        data = clap_model.get_audio_embeddings([paths], resample=True)

        if options['use_gpu']:
            data, labels = data.cuda(), labels.cuda()

        
        with torch.set_grad_enabled(True):
            optimizer.zero_grad()
            x, y = net(data, mixup_lambda=None, infer_mode=False, return_feature=True)
            logits, loss, loss_o = criterion(x, y, labels.long())
            
            loss.backward()
            optimizer.step()
        
        losses.update(loss.item(), labels.size(0))
        loss_o_meter.update(loss_o.item(), labels.size(0))


        if (batch_idx+1) % options['print_freq'] == 0:
            print("Batch {}/{}\t Loss {:.6f} ({:.6f})\t Loss_o {:.6f} ({:.6f})" \
                  .format(batch_idx+1, len(trainloader), losses.val, losses.avg, loss_o_meter.val, loss_o_meter.avg))
        
        loss_all += losses.avg

    return loss_all
