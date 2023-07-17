from glob import glob
# import io
# import json
from os import makedirs
from os.path import (dirname, exists, basename, splitext)
from pathlib import Path
import re
# import shutil
# import sys

import imageio.v3 as imageio
from skimage.transform import resize
from skimage.util import img_as_ubyte

__all__ = ["AssetsManager"]

IMAGE_EXTS = ["jpg", 'jpeg', 'png', 'gif']
VIDEO_EXTS = ["mp4"]

IMAGE_VARIANT_RE = re.compile(r'^.+(-(?:orig|\d+x\d+))\.[a-z]+$')

def getImageVariant(image_path):
    return IMAGE_VARIANT_RE.match(basename(image_path)).group(1)


def read_image(image_path):
    return imageio.imread(image_path)


def write_image(image_path, image):
    """converts image to uint8 prior to saving"""
    imageio.imwrite(image_path, img_as_ubyte(image))


def resize_image(image, width, height):
    """returns resized image data as RGB, stripping alpha channel"""
    return resize(image, (width, height))[..., :3]


def read_video(video_path):
    return imageio.get_reader(video_path)


def compute_aspect_ratio(width, height):
    return width / height

    
def resize_image_dir(images_path, req_width, req_height):
    req_ar = compute_aspect_ratio(req_width, req_height)

    imagePaths = set({})
    for pth in Path(images_path).iterdir():
        if pth.is_file():
            # print(f"is file: {pth} SKIPPING")
            continue
        # print(pth)
        image_files = glob(f"{pth}/*.*")
        # print(image_files)
        image_variants = {getImageVariant(fn):fn for fn in image_files}
        # print(json.dumps(image_variants, indent=4))
        if f"{req_width}x{req_height}" in image_variants:
            # image variant of requested dimensions already exists
            continue

        # try to use higher resolution if available
        for std_size in ["512", "256", "128"]:
            curr = f"-{std_size}x{std_size}"
            if curr in image_variants:
                imagePaths.add(image_variants[curr])
                break
        else:
            imagePaths.add(image_variants["-orig"])
        # continue
        #     # (fn, ext) = splitext(pth)
        #     # if ext[1:] in SOURCE_EXTS:
        #     #     imagePaths.add(pth)
        #     # else:
        #     #     print(f"ignoring unsupported file: {pth}")
    # print(imagePaths)
    # return

    for img_pth in sorted(imagePaths):
        noExt, ext = splitext(img_pth)
        dn, bn = dirname(img_pth), basename(img_pth)
        img_name = basename(dn)
        bn = basename(noExt)
        # print(f"noExt:{noExt}, ext:{ext} bn:{bn}")
        img = read_image(img_pth)
        [img_width, img_height, num_channels] = img.shape
        img_ar = compute_aspect_ratio(img_width, img_height)
        if img_ar == req_ar:
            # print(f"image: {bn}.{ext[1:]} {img_width, img_height}")
            if not exists(dn):
                print(f"creating dir: {dn}")
                makedirs(dn)
                pass
            new_pth = Path(dn) / Path(f"{img_name}-{req_width}x{req_height}{ext}")
            if not exists(new_pth):
                new_img = resize_image(img, req_width, req_height)
                print(f"creating: {new_pth}")
                write_image(new_pth, new_img)
        else:
            print(f"SKIPPING: {bn}.{ext[1:]}{img_width, img_height} has different aspect ratio than {req_width, req_height}")

        # if not exists(noExt):
        #     print(f"creating dir {noExt}")
        #     # makedirs(noExt)


    
# def get_resized_image(base_image_path, width, height):
#     pass


def _init_simple_dir(base_path, allowed_file_extensions=[], force_overwrite=False):
    if not base_path.exists():
        print(f"creating directory: {base_path}")
    for pth in base_path.iterdir():
        if pth.is_file():
            bn, ext = pth.stem, pth.suffix[1:]
            if ext in allowed_file_extensions:                    
                img_dir = base_path / Path(bn)
                img_dir.mkdir(parents=True, exist_ok=True)
                new_pth = img_dir / Path(f"{bn}-orig.{ext}")
                # shutil.move(pth, new_pth)
                if not new_pth.exists() or force_overwrite:
                    print(f"moving {pth} => {new_pth}")
                    pth.replace(new_pth)
                else:
                    print("not clobbering existing file")




class AssetsManager():
    """
    A class for managing face renactment assets in standardized manner, priortizing the saving of
    CPU/GPU cyles at the expense of requiring some extra disk space.

    
    I got sick of various Google Colabs eating up all my precious Colab Pro GPU units doing stuff like:
        * storing files in temporary locations
        * constantly resizing previously resized images/videos
        * constantly converting betweeen videos and arrays of images (frames)

    The goal is to make this package easy to install and use, allowing one to simply modify any of such colab's code
    which asks for an asset (image or video) with specific (width, height) dimensions to get resized to simply request it 
    from the asset manager, which will grab previously saved data if it exists, and if not, save the converted asset to disk 
    before returning it.

    I was inspired to do this, as I've already had success updated numerous Colabs to stop constantly wasting GPU cyles doing git checkouts 
    each time I start a new session, by saving the checkouts to a google drive location, and simply creating symlinks to them from 
    the colab's /content dir.  I've had luck creating symlinks so that various model files will also be cached on google drive, so
    that the won't be downloaded each session.
    
    I *think* I can even make use of virtualenvs if people didn't do stuff such as imports within the bodies of functions :(
    
    Of course, I suppose the real solution is for me to get a machine with a decent GPU

    Also, none of this actually requires a GPU, so you can add assets. and request them to be resized on your
    local machine, and your colabs will simply read in the pre-generated content

    This allows you store your images in a permanent location, such as ~/Google Drive/My Drive/assets
    and imposes a standardized hierarchy
    {assets_dir}/
        sources/
            {image1_basename}/
                {image1_basename}-orig.{image1_file_extension}
                {image1_basename}-256x256.{image1_file_extension}
            {image2_basename}/
                {image2_basename}-orig.{image2_file_extension}
                {image2_basename}-512x512.{image2_file_extension}
        drivers/
            {driver1_basename}/
                orig/
                    {driver1_basename}-orig.{}
    """
    base_path = None
    images_path = None
    videos_path = None
    generated_path = None

    def __init__(self, base_path):
        base = Path(base_path).expanduser()
        if not base.exists():
            makedirs(base)
        self.base_path = base
        self.images_path = self.base_path / Path("images")
        self.videos_path = self.base_path / Path("videos")
        self.generated_path = self.base_path / Path("generated")
    

    def disp_paths(self):
        print(f"""
        base path: {self.base_path}
        images_path: {self.images_path}
        videos_path: {self.videos_path}
        generated_path: {self.generated_path}
        """)


    def initialize_dirs(self, init_images=False, init_videos=False, init_generated=True):
        if init_images:
            self._initialize_images_dir()
        if init_videos:
            self._initialize_videos_dir()
        if init_generated:
            self._initialize_generated_dir()

    
    def _initialize_images_dir(self, force_overwrite=False):
        f"""
        if the directory doesn't exist, simply creates an empty directory

        else, if the directory isn't organized in the manner described below,
        converts it from a flat directory of image files, such as:

        image1.png
        image2.jpeg
            
        to a hierarchy of subdirs of the following format:

        image1/
            image1-orig.png
        image2/
            image2-orig.jpeg
        
        files of type other than {IMAGE_EXTS} will be ignored
        """
        # # create the dir, including any missing parents, if it/they don't exist
        # if not self.sources_path.exists:

        # self.sources_path.mkdir(parents=True, exist_ok=True)
        # create, or if already exists and has contents re-organize it, if necessary
        _init_simple_dir(self.images_path, IMAGE_EXTS, force_overwrite)

        # for pth in self.sources_path.iterdir():
        #     if pth.is_file():
        #         bn, ext = pth.stem, pth.suffix[1:]
        #         # bn, dot_ext = splitext(basename(pth))
        #         # ext = dot_ext[1:]
        #         if ext in SOURCE_EXTS:                    
        #             img_dir = self.sources_path / Path(bn)
        #             img_dir.mkdir(parents=True, exist_ok=True)
        #             new_pth = img_dir / Path(f"{bn}-orig.{ext}")
        #             print(f"{pth} => {new_pth}")
        #             # shutil.move(pth, new_pth)
        #             if not new_pth.exists() or force_overwrite:
        #                 pth.replace(new_pth)
        #             else:
        #                 print("not clobbering existing file")

    def _initialize_videos_dir(self):
        for pth in self.videos_path.iterdir():
            print(pth)


    def _initialize_generated_dir(self):
        pass


    def resize_source_images(self, width, height):
        resize_image_dir(self.images_path, width, height)


    def create_thumbnails(self):
        resize_image_dir(self.images_path, 128, 128)


    def get_thumbnail(self, base_name):
        return self.get_image(base_name, 128, 128)
    

    def get_image(self, base_name, width, height):
        """
        determines file extension for image identified by base_name and if it a variant with
        the desired dimensions doesn't already exists, creates and saves one prior to returning it
        """
        noExt = self.images_path / Path(base_name) / Path(f"{base_name}-{width}-{height}")
        matches = glob(f"{noExt}.*")
        if matches:
            return read_image(matches[0])
        else:
            orig = glob(f"{self.images_path}/{base_name}/{base_name}-orig.*")[0]
            orig_img = read_image(orig)
            return resize_image(orig_img, width, height)

    def get_thumbnails(self):
        thumbs = {basename(dirname(thumb)): read_image(thumb) for thumb in sorted(glob(f"/{self.images_path}/**/*-128x128.*"))}
        return thumbs
