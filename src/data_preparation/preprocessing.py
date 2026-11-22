"""Optional model-input transforms; disk images retain their native pixel range."""
from pathlib import Path
import torch
from torchvision import tv_tensors
from torchvision.transforms import v2
from .config import EXCLUDED_PREFIXES
from .images import read_rgb

def letterbox(image,boxes_xywh,target_size):
    height,width = image.shape[-2:]
    target_width,target_height = target_size
    if min(width,height,target_width,target_height) <= 0:
        raise ValueError("Positive input dimensions required")
    scale = min(target_width/width,target_height/height)
    new_width,new_height = max(1,round(width*scale)),max(1,round(height*scale))
    left,top = (target_width-new_width)//2,(target_height-new_height)//2
    boxes = tv_tensors.BoundingBoxes(torch.as_tensor(boxes_xywh,dtype=torch.float32).reshape(-1,4),
                                     format="XYWH",canvas_size=(height,width))
    transform = v2.Compose([v2.Resize((new_height,new_width),antialias=True),
                             v2.Pad([left,top,target_width-new_width-left,target_height-new_height-top],fill=114)])
    return transform(image,boxes)

def fit_training_statistics(dataset,target_size=None):
    """Fit channel statistics using original images in a loaded training split."""
    # Fit only on unaugmented training images, using PyTorch channel reductions.
    if dataset.get("split") != "train":
        raise ValueError("Fit statistics on the training split only")
    total,squared,count = torch.zeros(3,dtype=torch.float64),torch.zeros(3,dtype=torch.float64),0
    for row in dataset["rows"]:
        if row.get("augmentation_variant", 0) != 0:
            continue
        if Path(row["image"]["file_name"]).name.lower().startswith(EXCLUDED_PREFIXES):
            continue
        image = read_rgb(row["path"])
        if target_size is not None:
            image,_ = letterbox(image,[],target_size)
        values = v2.ToDtype(torch.float64,scale=True)(image)
        total += values.sum(dim=(1,2))
        squared += values.square().sum(dim=(1,2))
        count += image.shape[-2]*image.shape[-1]
    if count == 0:
        raise ValueError("Empty training dataset")
    mean = total/count
    std = (squared/count-mean.square()).clamp_min(0).sqrt()
    if torch.any(std < 1e-6):
        raise ValueError("Near-constant image channel")
    return mean.float(),std.float()

def model_input(row,target_size=None,mean=None,std=None):
    image = read_rgb(row["path"])
    boxes = tv_tensors.BoundingBoxes(torch.tensor([a["bbox"] for a in row["annotations"]],
                      dtype=torch.float32).reshape(-1,4),format="XYWH",canvas_size=tuple(image.shape[-2:]))
    if target_size is not None:
        image,boxes = letterbox(image,boxes,target_size)
    image = v2.ToDtype(torch.float32,scale=True)(image)
    if (mean is None) != (std is None):
        raise ValueError("Supply both mean and standard deviation")
    if mean is not None:
        mean,std = torch.as_tensor(mean),torch.as_tensor(std)
        if mean.shape != (3,) or std.shape != (3,) or not torch.isfinite(mean).all() or not torch.isfinite(std).all() or torch.any(std <= 0):
            raise ValueError("Three finite means and positive standard deviations required")
        image = v2.Normalize(mean.tolist(),std.tolist())(image)
    return dict(image=image.as_subclass(torch.Tensor),
                boxes=v2.ConvertBoundingBoxFormat("XYXY")(boxes).as_subclass(torch.Tensor),
                labels=torch.tensor([a["category_id"] for a in row["annotations"]],dtype=torch.int64))
