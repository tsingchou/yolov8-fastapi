from ultralytics import YOLO

yolo = YOLO("./20230510.pt", task="detect")
result = yolo(
    source="http://jsxk-household-inspection.oss-cn-hangzhou.aliyuncs.com/app/202305/d578098b32b659dc12f5d1c01f3daf16.jpg",
    save=True,
    conf=0.25,
    # device="cpu",
)
