from ultralytics import YOLO
from PIL import Image

model = YOLO('/Users/thaiduong/Desktop/python/webcam_capture_app_mac/runs/detect/train3/weights/best.pt')

results = model('/Users/thaiduong/Desktop/python/webcam_capture_app_mac/test4.jpg')

for r in results:
    im_array = r.plot()
    im = Image.fromarray(im_array[..., ::-1])
    im.show()
    im.save('kq.jpg')
