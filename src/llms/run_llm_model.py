import ollama
import argparse
import json
import pandas as pd


def run_model(model, image_paths, stream=True, show=False):
    if not isinstance(image_paths, list):
        image_paths = [image_paths]

    # TODO: Display the images (and prompt?) if asked
    if show:
        pass

    if stream:
        response = _run_model_streaming(model, image_paths)
    else:
        response = _run_model_standard(model, image_paths)

    return response

def _run_model_standard(model, image_paths, show=False):
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

def _run_model_streaming(model, image_paths, show=False):
    chunks = []
    # Define the model and the input prompt
    for chunk in ollama.chat(
        model = model,
        messages = [
            {
                'role': 'user',
                'images': image_paths
            }
        ],
        stream=True
    ): 
        text_piece = chunk['message']['content']
        chunks.append(text_piece)

    full_text = "".join(chunks)
    return full_text



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

    parser.add_argument('--outfile','-o', default=None, help='File to write results to')
    # Parse Args
    args = parser.parse_args()

    if args.imagepaths and args.imagelist:
        raise ValueError('Cannot provide both --imagelist (-L) and --imagepaths (-i) to the model. Please provide only one!')
    
    image_list = args.imagepaths
    if not image_list:
        image_list = _parse_filelist(args.imagelist)

    return args.model, image_list, args.outfile

def _parse_filelist(filepath):
    files = {}
    with open(filepath, 'r') as f:
        for line in f:
            if ':' in line:
                key, value = line.strip().split(':',1)
                files[key] = value.strip()

    return files

def _convert_pdf_to_image():
    return

if __name__ == '__main__':
    model, image_list, outfile = parse_args()

    if outfile:
        with open(outfile, 'w+') as f:
            f.write('\n\nTest Run __\n\n')
            f.write('name, score, fix\n')

    results = {}
    # Run model
    output = run_model(model, image_list)
    # Clean json
    output = output.replace('json','').replace('`', '').strip()
    
    data = json.loads(output)
    print(data)

    # for name, img_paths in image_list.items():
    #     output = run_model(model, img_paths)
    #     # Clean json
    #     output = output.replace('json','').replace('`', '').strip()
    #     # data
    #     data = json.loads(output)
    #     try:
    #         #print(data)
    #         if isinstance(data, list):
    #             data = data[0]
    #         #print(data)
    #         results[name] = data
            
    #         # Make it more readable
    #         result_string = f"{name}, {data.values()[0]}, {data.values()[1]}"
    #         if outfile:
    #             with open(outfile, 'a') as f:
    #                 f.write(f'{result_string}\n')
    #         print(result_string)
    #     except Exception as e:
    #         print(f'{name}: {data} -- {e}')

    print(pd.DataFrame(results))
    print('Done!')

        

