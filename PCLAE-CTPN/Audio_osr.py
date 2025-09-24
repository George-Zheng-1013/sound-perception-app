import csv
import os
import argparse
import datetime
import time
import pandas as pd
import importlib
import torch
import torch.nn as nn
from torch.optim import lr_scheduler
import torch.backends.cudnn as cudnn
import config
from datasets.Audio_OSR_dataloader import AudioDatasetLoader
from models.htsat import HTSAT_Swin_Transformer
from msclap import CLAP
from utils import Logger, save_networks, load_networks
from core import train, test


# 使用相对路径替代硬编码路径
project_root = os.path.dirname(os.path.abspath(__file__))
dataset_dir = os.path.join(project_root, "DATASET")

dataset_config = {
    "meta_csv": os.path.join(dataset_dir, "meta.csv"),
    "audio_path": os.path.join(dataset_dir, "audio"),
}

parser = argparse.ArgumentParser("Training")

# 使用相对路径作为默认值
parser.add_argument("--outf", type=str, default=project_root)
parser.add_argument("--save-dir", type=str, default=project_root)

# Dataset
parser.add_argument(
    "--dataset", type=str, default="ESC_48", help="ESC_48 | UrbanSound8K"
)
parser.add_argument("--audio_dir", type=str, default=dataset_config["audio_path"])
parser.add_argument("--meta_dir", type=str, default=dataset_config["meta_csv"])
parser.add_argument("--fold", type=int, default=1)
parser.add_argument("--outf", type=str, default=r"D:\PCLAE-CTPN")
parser.add_argument("--out-num", type=int, default=50, help="For CIFAR100")
parser.add_argument("--num", type=int, default=1)
parser.add_argument("--class", type=str, default="ESC48_CTPN")

# optimization
parser.add_argument("--batch-size", type=int, default=64)
parser.add_argument("--lr", type=float, default=0.01, help="learning rate for model")
parser.add_argument("--max-epoch", type=int, default=100)
parser.add_argument("--stepsize", type=int, default=30)
parser.add_argument("--temp", type=float, default=1, help="temp")
parser.add_argument("--num_centers", type=int, default=1)

# model
parser.add_argument(
    "--weight-pl", type=float, default=0.1, help="weight for center loss"
)
parser.add_argument("--beta", type=float, default=0.1, help="weight for entropy loss")
parser.add_argument("--model", type=str, default="classifier32")

# misc
parser.add_argument("--nz", type=int, default=100)
parser.add_argument("--ns", type=int, default=1)
parser.add_argument("--eval-freq", type=int, default=1)
parser.add_argument("--print-freq", type=int, default=5)
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--use-gpu", action="store_true", default=True)
parser.add_argument("--gpu", type=str, default="0")
parser.add_argument("--save-dir", type=str, default=r"D:\PCLAE-CTPN")
parser.add_argument("--loss", type=str, default="ARPLoss")
parser.add_argument("--eval", action="store_true", help="Eval", default=False)
parser.add_argument("--cs", action="store_true", help="Confusing Sample", default=False)


def main_worker(options):
    torch.manual_seed(options["seed"])
    os.environ["CUDA_VISIBLE_DEVICES"] = options["gpu"]

    if options["eval"]:
        print("--------------->Evaluating<---------------")
    else:
        print("--------------->Training<-----------------")

    if options["use_gpu"]:
        print("Currently using GPU: {}".format(options["gpu"]))
        cudnn.benchmark = True
        torch.cuda.manual_seed_all(options["seed"])
    else:
        print("Currently using CPU")

    print("-----------------------------------------------")

    # Dataset
    print("{} Preparation".format(options["dataset"]))
    Data = AudioDatasetLoader(
        audio_dir=options["audio_dir"],
        meta_dir=options["meta_dir"],
        known=options["known"],
        unknown=options["unknown"],
        batch_size=options["batch_size"],
    )
    trainloader, testloader, outloader = (
        Data.train_loader,
        Data.test_loader,
        Data.out_loader,
    )

    options["num_classes"] = Data.num_classes
    print("number of known classes:", options["num_classes"])

    net = HTSAT_Swin_Transformer(
        spec_size=config.htsat_spec_size,
        patch_size=config.htsat_patch_size,
        in_chans=1,
        num_classes=options["num_classes"],
        window_size=config.htsat_window_size,
        config=config,
        depths=config.htsat_depth,
        embed_dim=config.htsat_dim,
        patch_stride=config.htsat_stride,
        num_heads=config.htsat_num_head,
    )

    feat_dim = 128

    # Loss
    options.update({"feat_dim": feat_dim})

    Loss = importlib.import_module("loss." + options["loss"])
    criterion = getattr(Loss, options["loss"])(**options)

    if options["use_gpu"]:
        net = nn.DataParallel(net).cuda()
        criterion = criterion.cuda()

    model_path = os.path.join(options["outf"], "models", options["class"])
    if not os.path.exists(model_path):
        os.makedirs(model_path)

    file_name = "{}_{}_{}_{}".format(
        options["model"], options["loss"], options["item"], options["cs"]
    )

    # Load and initialize CLAP
    clap_model = CLAP(
        os.path.join(os.path.dirname(__file__), "CLAP_weights_2023.pth"),
        version="2023",
        use_cuda=False,
    )

    if options["eval"]:
        net, criterion = load_networks(net, model_path, file_name, criterion=criterion)
        results = test(
            net,
            criterion,
            testloader,
            outloader,
            epoch=0,
            clap_model=clap_model,
            **options
        )
        print(
            "Acc (%): {:.3f}\t AUROC (%): {:.3f}\t OSCR (%): {:.3f}\t".format(
                results["ACC"], results["AUROC"], results["OSCR"]
            )
        )

        return results

    params_list = [{"params": net.parameters()}, {"params": criterion.parameters()}]

    optimizer = torch.optim.SGD(
        params_list, lr=options["lr"], momentum=0.9, weight_decay=1e-4
    )

    if options["stepsize"] > 0:
        scheduler = lr_scheduler.MultiStepLR(optimizer, milestones=[30, 60, 90, 120])

    start_time = time.time()
    best_performance = 0
    for epoch in range(options["max_epoch"]):
        print("==> Epoch {}/{}".format(epoch + 1, options["max_epoch"]))

        train(
            net,
            criterion,
            optimizer,
            trainloader,
            epoch=epoch,
            clap_model=clap_model,
            **options
        )

        if (
            options["eval_freq"] > 0
            and (epoch + 1) % options["eval_freq"] == 0
            or (epoch + 1) == options["max_epoch"]
        ):
            print("==> Test", options["loss"])
            results = test(
                net,
                criterion,
                testloader,
                outloader,
                epoch=epoch,
                clap_model=clap_model,
                **options
            )
            print(
                "Acc (%): {:.3f}\t AUROC (%): {:.3f}\t OSCR (%): {:.3f}\t".format(
                    results["ACC"], results["AUROC"], results["OSCR"]
                )
            )

            # 如果验证集性能提高，则更新最佳性能和模型参数
            if results["OSCR"] > best_performance:
                best_performance = results["OSCR"]
                save_networks(net, model_path, file_name, criterion=criterion)

        if options["stepsize"] > 0:
            scheduler.step()

    elapsed = round(time.time() - start_time)
    elapsed = str(datetime.timedelta(seconds=elapsed))
    print("Finished. Total elapsed time (h:m:s): {}".format(elapsed))

    return results


if __name__ == "__main__":
    args = parser.parse_args()
    options = vars(args)
    results = dict()

    from split import splits_2020 as splits

    for i in range(len(splits[options["dataset"]])):
        known = splits[options["dataset"]][len(splits[options["dataset"]]) - i - 1]
        unknown = list(set(list(range(0, 64))) - set(known))

        print("--------------------------------------------")
        print("selected known classes:", len(known))
        print("selected unknown classes:", len(unknown))

        options.update(
            {
                "item": i,
                "known": known,
                "unknown": unknown,
            }
        )

        dir_name = "{}_{}".format(options["model"], options["loss"])
        dir_path = os.path.join(options["outf"], "results", dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        file_name = "{}_{}.csv".format(options["dataset"], "CTPN")

        res = main_worker(options)
        res["unknown"] = unknown
        res["known"] = known
        results[str(i)] = res
        df = pd.DataFrame(results)
        df.to_csv(os.path.join(dir_path, file_name))
