from ultralytics import YOLO


# Load a pretrained YOLO model (recommended for training)
model = YOLO("yolov8n.pt")

# Train the model using the 'coco8.yaml' dataset for 3 epochs
results = model.train(data="mydata_biaso7_8.yaml", epochs=70, batch=1, workers=0)


