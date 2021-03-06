import torch
import torchvision.transforms as transforms
import torch.nn as nn
import torchvision
import argparse
import utils
from model import Network
from torchsummary import summary
from tqdm import tqdm
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"


def get_args():
    parser = argparse.ArgumentParser("Single_Path_One_Shot")
    parser.add_argument('--train_dir', type=str, default='/home/lushun/Documents/Dataset/ImageNet/train',
                        help='path to training dataset')
    parser.add_argument('--val_dir', type=str, default='/home/lushun/Documents/Dataset/ImageNet/val',
                        help='path to validation dataset')
    parser.add_argument('--train_batch', type=int, default=128, help='batch size')
    parser.add_argument('--val_batch', type=int, default=2048, help='batch size')
    parser.add_argument('--epochs', type=int, default=1000, help='batch size')
    parser.add_argument('--learning_rate', type=float, default=0.1, help='initial learning rate')
    parser.add_argument('--momentum', type=float, default=0.9, help='momentum')
    parser.add_argument('--weight-decay', type=float, default=4e-5, help='weight decay')
    parser.add_argument('--train_interval', type=int, default=200, help='print frequency')	
    parser.add_argument('--val_interval', type=int, default=5, help='save frequency')
    args = parser.parse_args()
    return args


def main():
    args = get_args()

    transform = transforms.Compose(
        [transforms.ToTensor(),
         transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))])
    trainset = torchvision.datasets.CIFAR10(root='./data', train=True,
                                            download=True, transform=transform)
    train_loader = torch.utils.data.DataLoader(trainset, batch_size=args.train_batch,
                                              shuffle=True, num_workers=0)
    valset = torchvision.datasets.CIFAR10(root='./data', train=False,
                                           download=True, transform=transform)
    val_loader = torch.utils.data.DataLoader(valset, batch_size=args.val_batch,
                                             shuffle=False, num_workers=0)

    model = Network(classes=10, gap_size=1)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(filter(lambda p: p.requires_grad, model.parameters()), lr=args.learning_rate,
                                momentum=args.momentum, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda epoch: 1-(epoch / args.epochs))

    if torch.cuda.is_available():
        print('Train on GPU!')
        criterion = criterion.cuda()
        device = torch.device("cuda")
    else:
        criterion = criterion
        device = torch.device("cpu")
    model = model.to(device)
    summary(model, (3, 32, 32))
    print('Start training!')
    for epoch in range(args.epochs):
        lr = scheduler.get_lr()
        print('epoch:%d, lr:%f' % (epoch, scheduler.get_lr()[0]))
        train(args, epoch, train_loader, device, model, criterion, optimizer)
        scheduler.step()
        # if (epoch + 1) % args.val_interval == 0:
        validate(args, epoch, val_loader, device, model)


def train(args, epoch, train_data, device, model, criterion, optimizer):
    _loss = 0.0
    for step, (inputs, labels) in enumerate(tqdm(train_data)):
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        _loss += loss.item()
        if (step+1) % args.train_interval == 0:
            print('[epoch:%d, step:%d] loss: %f' % (epoch, step + 1, _loss / (step + 1)))
    print('[epoch:%d, step:%d] loss: %f' % (epoch, step + 1, _loss / (step+1)))


def validate(args, epoch, val_data, device, model):
    top1 = utils.AvgrageMeter()
    top5 = utils.AvgrageMeter()
    with torch.no_grad():
        for step, (inputs, targets) in enumerate(tqdm(val_data)):
            inputs = inputs.to(device)
            labels = targets.to(device)
            outputs = model(inputs)
            prec1, prec5 = utils.accuracy(outputs, labels, topk=(1, 5))
            n = inputs.size(0)
            top1.update(prec1.item(), n)
            top5.update(prec5.item() , n)
        print('[Val_Accuracy] top1:%.5f%%, top5:%.5f%% ' % (top1.avg, top5.avg))
    # save model
    if (epoch+1) % args.val_interval == 0:
        save_dir = './snapshots/epoch_' + str(epoch+1) + '_acc_' + str('%.5f' % top1) + '-weights.pt'
        torch.save(model.state_dict(), save_dir)
        print('Successfully save the model.')


if __name__ == '__main__':
    main()
