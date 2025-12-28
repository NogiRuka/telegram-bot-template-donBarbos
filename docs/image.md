添加接口
POST
/Users/{Id}/Images/{Type}
Uploads an image for an item, must be base64 encoded.

Requires authentication as user

Parameters
Cancel
Reset
Name	Description
Id *
string
(path)
User Id

0e26758dc85d40488314f9d77d8c9a7d
Type *
string
(path)
Image Type


Primary
Index
integer($int32)
(query)
Image Index

Index


下面是一个成功的python示例

import base64
import requests

user_id = "0e26758dc85d40488314f9d77d8c9a7d"
token = "ffc295249f6040ff9d8dd6d28ef24360"
url = f"https://lustfulboy.com/emby/Users/{user_id}/Images/Primary"

with open("duitang911849.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

headers = {
    "Content-Type": "image/jpeg", 
    "X-Emby-Token": token
}

r = requests.post(url, headers=headers, data=b64)
print(r.status_code, r.text)
