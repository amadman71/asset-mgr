from assets_mgr import AssetsManager

if __name__ == "__main__":
    am = AssetsManager("~/Google Drive/My Drive/assets")
    # am.disp_paths()
    # am.move_base_images_to_dirs()
    # am.resize_source_images(512, 512)
    # resize_image_dir(sys.argv[1], 256, 256)
    # am.create_thumbnails()
    for (k, v) in am.get_thumbnails():
        print(k, v.path)
