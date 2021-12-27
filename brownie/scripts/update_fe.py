import os
import shutil 
import yaml
import json

def update_front_end():
    copy_folders_to_front_end("./build", "../../charity-raffle-front-end/src/chain-info")
    with open("brownie-config.yaml", "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        with open("../../charity-raffle-front-end/src/config.json", "w") as f:
            f.write(json.dumps(config))
        print("Updated front end config.")

def copy_folders_to_front_end(src, dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

def main():
    update_front_end()

