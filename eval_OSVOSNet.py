import os
import argparse
import sys
import time
import numpy as np
import cv2
import torch
import configparser
import torchvision.transforms.functional as TF
from PIL import Image

from src.network import OSVOSNet
from src.dataset import WaterDataset_RGB
from src.avg_meter import AverageMeter
from src.cvt_images_to_overlays import run_cvt_images_to_overlays
from src.utils import load_image_in_PIL, iou_tensor


def eval_OSVOSNetNet():
    
    # Paths
    cfg = configparser.ConfigParser()
    cfg.read('settings.conf')

    if sys.platform == 'darwin':
        cfg_dataset = 'dataset_mac'
    elif sys.platform == 'linux':
        cfg_dataset = 'dataset_ubuntu'

    # Hyper parameters
    parser = argparse.ArgumentParser(description='PyTorch OSVOSNet Testing')
    parser.add_argument(
        '-c', '--checkpoint', default=None, type=str, metavar='PATH',
        help='Path to latest checkpoint (default: none).')
    parser.add_argument(
        '-v', '--video-name', default=None, type=str,
        help='Test video name (default: none).')
    parser.add_argument(
        '-m', '--model-name', default='OSVOSNet', type=str,
        help='Model name for the ouput segmentation, it will create a subfolder under the out_folder.')
    parser.add_argument(
        '-o', '--out-folder', default=cfg['paths'][cfg_dataset], type=str, metavar='PATH',
        help='Folder for the output segmentations.')
    parser.add_argument(
        '-b', '--benchmark', action='store_true',
        help='Evaluate the video with groundtruth.')
    args = parser.parse_args()

    print('Args:', args)

    if args.checkpoint is None:
        raise ValueError('Must input checkpoint path.')
    if args.video_name is None:
        raise ValueError('Must input video name.')

    water_thres = 0.5

    device = torch.device('cpu')
    if torch.cuda.is_available():
        device = torch.device('cuda')

    # Dataset
    dataset_args = {}
    if torch.cuda.is_available():
        dataset_args = {
            'num_workers': int(cfg['params_OSVOS']['num_workers']),
            'pin_memory': bool(cfg['params_OSVOS']['pin_memory'])
        }

    dataset = WaterDataset_RGB(
        mode='eval',
        dataset_path=cfg['paths'][cfg_dataset], 
        test_case=args.video_name
    )
    eval_loader = torch.utils.data.DataLoader(
        dataset=dataset,
        batch_size=1,
        shuffle=False,
        **dataset_args
    )

    # Model
    OSVOS_net = OSVOSNet()

    # Load pretrained model
    if os.path.isfile(args.checkpoint):
        print('Load checkpoint \'{}\''.format(args.checkpoint))
        if torch.cuda.is_available():
            checkpoint = torch.load(args.checkpoint)
        else:
            checkpoint = torch.load(args.checkpoint, map_location='cpu')
        args.start_epoch = checkpoint['epoch'] + 1
        OSVOS_net.load_state_dict(checkpoint['model'])
        print('Loaded checkpoint \'{}\' (epoch {})'
                .format(args.checkpoint, checkpoint['epoch']))
    else:
        raise ValueError('No checkpoint found at \'{}\''.format(args.checkpoint))

    # Set ouput path
    out_path = os.path.join(args.out_folder, args.model_name + '_segs', args.video_name)
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    # Start testing
    OSVOS_net.to(device).eval()
    running_time = AverageMeter()
    running_endtime = time.time()
    
    # First frame annotation
    pre_frame_mask = dataset.get_first_frame_label()
    first_frame_seg = TF.to_pil_image(pre_frame_mask)
    first_frame_seg.save(os.path.join(out_path, '0.png'))
    pre_frame_mask = pre_frame_mask.unsqueeze(0).to(device)
    
    if args.benchmark:
        gt_folder = os.path.join(cfg['paths'][cfg_dataset], 'test_annots', args.video_name)
        gt_list = os.listdir(gt_folder)
        gt_list.sort(key = lambda x: (len(x), x))
        gt_list.pop(0)
    avg_iou = 0

    with torch.no_grad():
        for i, sample in enumerate(eval_loader):

            img = sample['img'].to(device)     

            outputs = OSVOS_net(img)

            output = outputs[-1].detach()
            output = 1 / (1 + torch.exp(-output))
            seg_raw = TF.to_pil_image(output.squeeze(0).cpu())
            seg_raw.save(os.path.join(out_path, '%d.png' % (i + 1)))

            running_time.update(time.time() - running_endtime)
            running_endtime = time.time()

            if args.benchmark:
                gt_seg = load_image_in_PIL(os.path.join(gt_folder, gt_list[i])).convert('L')
                gt_tf = TF.to_tensor(gt_seg).to(device).type(torch.int)

                iou = iou_tensor(pre_frame_mask.squeeze(0).type(torch.int), gt_tf)
                avg_iou += iou.item()
                print('iou:', iou.item())

            print('Segment: [{0:4}/{1:4}]\t'
                'Time: {running_time.val:.3f}s ({running_time.sum:.3f}s)\t'.format(
                i + 1, len(eval_loader), running_time=running_time))

    if args.benchmark:
        print('total_iou:', avg_iou)
        avg_iou /= len(eval_loader)
        print('avg_iou:', avg_iou, 'frame_num:', len(eval_loader))

    run_cvt_images_to_overlays(args.video_name, args.out_folder, args.model_name)
    
if __name__ == '__main__':
    eval_OSVOSNetNet()
