import ollama
import argparse
from PIL import Image
import json
import pandas as pd


def run_model(model, image_paths, show=False):
    client = ollama.Client()
    if not isinstance(image_paths, list):
        image_paths = [image_paths]

    path_resp = "\n\t".join(image_paths)

    # TODO: Display the images (and prompt?) if asked
    if show:
        pass

    # Define the model and the input prompt
    response = ollama.chat(
        model = model,
        messages = [
            {
                'role': 'user',
                'images': image_paths
            }
        ]
    )
    return response['message']['content']


def parse_args():
    parser = argparse.ArgumentParser(
        description='Script to process image files'
    )

    # Add image paths Argument
    parser.add_argument(
        '--imagepaths','-i',
        nargs='*',
        required=False,
        help='Provide path(s) to image files(s) to analyze'
    )

    parser.add_argument(
        '--imagelist','-L',
        help='Provide a file containing labels '
    )

    parser.add_argument(
        '--model','-m',
        default='walkability_rater',
        help='Choose a model to use to score these images'
    )
    # Parse Args
    args = parser.parse_args()

    if args.imagepaths and args.imagelist:
        raise ValueError('Cannot provide both --imagelist (-L) and --imagepaths (-i) to the model. Please provide only one!')
    
    image_list = args.imagepaths
    if not image_list:
        image_list = _parse_filelist(args.imagelist)

    return args.model, image_list

def _parse_filelist(filepath):
    files = {}
    with open(filepath, 'r') as f:
        for line in f:
            if ':' in line:
                key, value = line.strip().split(':',1)
                files[key] = value.strip()

    return files

if __name__ == '__main__':
    model, image_list = parse_args()

    OUTPUT_FILE = 'data/test/output'
    with open(OUTPUT_FILE, 'w+') as f:
        f.write('\n\nTest Run __\n\n')
        f.write('name, score, fix\n')

    results = {}
    for name, img_paths in image_list.items():
        output = run_model(model, img_paths)
        # Clean json
        output = output.replace('json','').replace('`', '').strip()
        # data
        data = json.loads(output)
        try:
            #print(data)
            if isinstance(data, list):
                data = data[0]
            #print(data)
            results[name] = data
            
            # Make it more readable
            result_string = f"{name}, {data.values()[0]}, {data.values()[1]}"
            with open(OUTPUT_FILE, 'a') as f:
                f.write(f'{result_string}\n')
            print(result_string)
        except Exception as e:
            print(f'{name}: {data} -- {e}')

    print(pd.DataFrame(results))
    print('Done!')

        

