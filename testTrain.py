from ultralytics import YOLO
from PIL import Image

model = YOLO('/Users/thaiduong/Desktop/python/webcam_capture_app_mac/my_model.pt')

results = model('/Users/thaiduong/Desktop/python/webcam_capture_app_mac/original_bia7.jpg')

for r in results:
    im_array = r.plot()
    im = Image.fromarray(im_array[..., ::-1])
    im.show()
    im.save('kq.jpg')
