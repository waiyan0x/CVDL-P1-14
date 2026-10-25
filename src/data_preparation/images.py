"""OpenCV decoding/encoding and image fingerprints; Pillow handles AVIF fallback."""
from pathlib import Path
import hashlib
import cv2
import numpy as np
import torch
from torchvision import tv_tensors
from PIL import Image as PillowImage

def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def read_rgb(path):
    # imdecode also handles Windows paths containing non-ASCII characters.
    array = cv2.imdecode(np.fromfile(path,dtype=np.uint8),cv2.IMREAD_COLOR)
    if array is None:
        # OpenCV's Windows wheel lacks AVIF; some source .jpg files contain AVIF.
        with PillowImage.open(path) as encoded:
            if encoded.format != "AVIF":
                raise ValueError(f"Cannot decode image with OpenCV: {path}")
            rgb = np.array(encoded.convert("RGB"),copy=True)
    else:
        rgb = cv2.cvtColor(array,cv2.COLOR_BGR2RGB)
    return tv_tensors.Image(torch.from_numpy(rgb).permute(2,0,1).contiguous())

def write_rgb(image,path):
    rgb = image.detach().cpu().permute(1,2,0).contiguous().numpy()
    success,encoded = cv2.imencode(".png",cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),
                                   [cv2.IMWRITE_PNG_COMPRESSION,3])
    if not success:
        raise ValueError(f"Cannot encode image: {path}")
    encoded.tofile(path)

def image_info(path):
    image = read_rgb(path)
    _,height,width = image.shape
    rgb = image.permute(1,2,0).contiguous().numpy()
    pixels = hashlib.sha256(str((width,height)).encode()+rgb.tobytes()).hexdigest()
    gray = cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    values = cv2.resize(gray,(9,8),interpolation=cv2.INTER_AREA)
    dhash = sum(int(bit) << index for index,bit in
                enumerate((values[:,:-1] > values[:,1:]).reshape(-1)))
    return dict(width=width,height=height,pixel_hash=pixels,dhash=dhash)
