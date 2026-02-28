POST
/Sessions/{Id}/Message
Issues a command to a client to display a message to the user

Requires authentication as user

Parameters
Cancel
Name	Description
Id *
string
(path)
Session Id

2e18e75f670318938341d002613a2a07
Text *
string
(query)
The message text.

嘿～我发现你正在用网页端播放视频了 👀 不过这里暂时不支持网页端观看哦～  请切换到官方客户端继续播放吧！ 这次就当作我没看见 😉
Header *
string
(query)
The message header.

桜色男孩⚣｜网页播放小侦测 🤖
TimeoutMs
integer($int64)
(query)
The message timeout. If omitted the user will have to confirm viewing the message.

TimeoutMs
