import os
import argparse

root_folder = '/Ship01/Dataset/water/'
full_videos = ['stream0', 'stream1', 'stream3_small', 'stream4', 'boston_harbor2_small_rois', 'buffalo0_small', 'canal0', 'mexico_beach_clip0', 'holiday_inn_clip0', 'gulf_crest', 'pineapple_willy_clip0', 'pineapple_willy_clip1']

test_videos = full_videos
list_name = 'eval_addon.txt' # 'eval_all.txt'

def get_sequence_list():
    
    with open(os.path.join(root_folder, list_name), 'r') as f:
        tmp = f.readlines()
        sequence_list = [x.strip() for x in tmp]
    
    try:
        sequence_list.remove('')
    except ValueError as e:
        pass

    print('Seq names:', sequence_list)
    return sequence_list


def get_scores(method_name):
    method_str = f' --method {method_name}'
    base_cmd = 'python3 /Ship01/SourcesArchives/VOS-evaluation/eval_waterdataset.py --update'
    cmd = base_cmd + method_str
    os.system(cmd)

def eval_WaterNet(args):

    
    sequence_list = get_sequence_list()
    base_cmd = 'python3 eval_WaterNet.py -c=models/cp_WaterNet_199.pth.tar'

    method_name = 'WaterNet'
    if args.no_aa:
        base_cmd += ' --no-aa'
        method_name += '_no_aa'
    if args.no_conf:
        base_cmd += ' --no-conf'
        method_name += '_no_conf'
    # method_name += '_segs'

    if not args.score:
        for seq in sequence_list:
            cmd = base_cmd + f' -v {seq}'
            if seq not in test_videos:
                cmd += ' --sample '
            os.system(cmd)
    
    get_scores(method_name)

def eval_OSVOS(args):
    
    sequence_list = get_sequence_list()

    if args.no_online:
        
        if not args.score:

            eval_cmd = 'python3 eval_OSVOSNet.py -c=models/cp_OSVOSNet_199.pth.tar --model-name=OSVOSNet'
            for seq in sequence_list:
                cmd = eval_cmd + f' -v {seq}'
                if seq not in test_videos:
                    cmd += ' --sample '
                os.system(cmd)
        
        get_scores('OSVOSNet')

    else:

        if not args.score:

            total_epochs = 230
            train_cmd = f'python3 train_OSVOSNet.py -c=models/cp_OSVOSNet_199.pth.tar --online --total-epochs {total_epochs}'
            eval_cmd = 'python3 eval_OSVOSNet.py --model-name=OSVOSNet_online'

            for seq in sequence_list:
                cmd = train_cmd + f' -v{seq}'
                os.system(cmd)

                cmd = eval_cmd + f' -v {seq}' + f' -c models/cp_OSVOSNet_{total_epochs-1}_{seq}.pth.tar'
                if seq not in test_videos:
                    cmd += ' --sample '
                os.system(cmd)

        get_scores('OSVOSNet_online')


def eval_MSK(args):

    sequence_list = get_sequence_list()

    if args.no_online:
        
        if not args.score:
            eval_cmd = 'python3 eval_RGBMaskNet.py -c=models/cp_RGBMaskNet_199.pth.tar --model-name=RGBMaskNet'
            for seq in sequence_list:
                cmd = eval_cmd + f' -v {seq}'
                if seq not in test_videos:
                    cmd += ' --sample '
                os.system(cmd)
        
        get_scores('RGBMaskNet')

    else:
        
        if not args.score:

            train_cmd = 'python3 train_RGBMaskNet.py -c=models/cp_RGBMaskNet_199.pth.tar --online'
            eval_cmd = 'python3 eval_RGBMaskNet.py --model-name=RGBMaskNet_online'

            for seq in sequence_list:
                cmd = train_cmd + f' -v{seq}'
                os.system(cmd)

                cmd = eval_cmd + f' -v {seq}' + f' -c models/cp_RGBMaskNet_229_{seq}.pth.tar'
                if seq not in test_videos:
                    cmd += ' --sample '
                os.system(cmd)

        get_scores('RGBMaskNet_online')


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Bencharmark')
    parser.add_argument(
        '--method', default=None, type=str, required=True,
        help='Input the method name (default: none).')
    parser.add_argument(
        '--score', action='store_true',
        help='Compute the scores without re-run the benchmark.')
    parser.add_argument(
        '--no-conf', action='store_true', 
        help='For WaterNet (default: none).')
    parser.add_argument(
        '--no-aa', action='store_true',
        help='For WaterNet (default: none).')
    parser.add_argument(
        '--no-online', action='store_true',
        help='For OSVOS and MSK (default: none).')
    args = parser.parse_args()

    print('Args:', args)

    if args.method == 'WaterNet':
        eval_WaterNet(args)
    elif args.method == 'OSVOS':
        eval_OSVOS(args)
    elif args.method == 'MSK':
        eval_MSK(args)

