# yolov8-fastapi
This is an API for detecting LPG inspection images using YOLOv8 and FastAPI.

## Quickstart
Before using this repository!
Please replace the weight file in /data/model/best.pt with your own trained model, unless you want to detect LPG inspection images.

## Installation
Build and start YOLOv8 with FASTAPI on http://localhost:9099
### Build
```docker-compose up```

### Rebuild
```docker-compose up --build```

## Usage
### Models
There are 2 Models in model.py:
```
# this is for user to login
class User(BaseModel):
    username: str
    password: str

# this is for image to predict
class ImageToPredict(BaseModel):
    type: str = 'url' # or 'base64'
    url: str = None
    base64: str = None
    date: str = None
```

### API
#### Login
```
http://localhost:9099/token
```

#### Predict
```
http://localhost:9099/token
```
Accepts URL or base64 image, and returns the prediction result in JSON format.

### Users
Users are stored in table ```users``` of ```./sysuser.sqlite```, and the default username and password are ```admin``` and ```admin```.
