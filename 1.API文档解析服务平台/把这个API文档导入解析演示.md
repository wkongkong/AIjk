# 天空空系统接口文档


**简介**:天空空系统接口文档


**HOST**:172.16.9.XXX:18090


**联系人**:


**Version**:2.0


**接口路径**:/user/v2/api-docs?group=default


[TOC]






# 角色报表分发服务


## 查询角色报表分发树列表及其勾选


**接口地址**:`/user/sysRoleReportAssign/getRoleReportTree`


**请求方式**:`POST`


**请求数据类型**:`application/json`


**响应数据类型**:`*/*`


**接口描述**:


**请求示例**:


```javascript
{
  "createBy": "",
  "createTime": "",
  "endTime": "",
  "id": "",
  "pageNum": "",
  "pageSize": "",
  "params": {},
  "remark": "",
  "reportCode": "",
  "roleCode": "",
  "searchKey": "",
  "sortNo": 0,
  "startTime": "",
  "updateBy": "",
  "updateTime": "",
  "validFlag": ""
}
```


**请求参数**:


| 参数名称 | 参数说明 | 请求类型    | 是否必须 | 数据类型 | schema |
| -------- | -------- | ----- | -------- | -------- | ------ |
|sysRoleReportAssignDTO|sysRoleReportAssignDTO|body|true|角色报表分发|角色报表分发|
|&emsp;&emsp;createBy|创建人||false|string||
|&emsp;&emsp;createTime|创建时间||false|string(date-time)||
|&emsp;&emsp;endTime|查询时间结束||false|string(date-time)||
|&emsp;&emsp;id|主键||false|string||
|&emsp;&emsp;pageNum|分页参数-当前页数||false|string||
|&emsp;&emsp;pageSize|分页参数-单页显示数||false|string||
|&emsp;&emsp;params|请求参数||false|object||
|&emsp;&emsp;remark|备注||false|string||
|&emsp;&emsp;reportCode|报表编码||false|string||
|&emsp;&emsp;roleCode|角色编码||false|string||
|&emsp;&emsp;searchKey|用于模糊搜索拼音码五笔码||false|string||
|&emsp;&emsp;sortNo|排序号||false|integer(int32)||
|&emsp;&emsp;startTime|查询时间开始||false|string(date-time)||
|&emsp;&emsp;updateBy|修改人||false|string||
|&emsp;&emsp;updateTime|修改时间||false|string(date-time)||
|&emsp;&emsp;validFlag|有效标志||false|string||


**响应状态**:


| 状态码 | 说明 | schema |
| -------- | -------- | ----- | 
|200|OK|响应消息体|
|201|Created||
|401|Unauthorized||
|403|Forbidden||
|404|Not Found||


**响应参数**:


| 参数名称 | 参数说明 | 类型 | schema |
| -------- | -------- | ----- |----- | 
|code|状态码：成功标记=1，失败标记=0|string||
|data|数据|object||
|extendInfo|扩展信息|string||
|message|返回信息|string||
|pageNum|页数|integer(int32)|integer(int32)|
|pageSize|页数大小|integer(int32)|integer(int32)|
|timestamp|返回时间|integer(int64)|integer(int64)|
|total|总条数|integer(int64)|integer(int64)|


**响应示例**:
```javascript
{
	"code": "",
	"data": {},
	"extendInfo": "",
	"message": "",
	"pageNum": 0,
	"pageSize": 0,
	"timestamp": 0,
	"total": 0
}
```


# 系统菜单字典服务


## 删除系统菜单字典信息


**接口地址**:`/user/sysMenuDict/deleteInfo`


**请求方式**:`POST`


**请求数据类型**:`application/json`


**响应数据类型**:`*/*`


**接口描述**:


**请求示例**:


```javascript
{
  "accessLevel": "",
  "appCode": "",
  "appName": "",
  "appSortNo": 0,
  "cacheFlag": "",
  "checked": true,
  "children": [
    {
      "accessLevel": "",
      "appCode": "",
      "appName": "",
      "appSortNo": 0,
      "cacheFlag": "",
      "checked": true,
      "children": [],
      "collected": true,
      "createBy": "",
      "createTime": "",
      "customCode": "",
      "doctorMiniAppMenuType": "",
      "endTime": "",
      "extLink": "",
      "filterMenuCode": "",
      "id": "",
      "keyword": "",
      "menuCode": "",
      "menuCodes": [],
      "menuDesc": "",
      "menuIcon": "",
      "menuName": "",
      "menuParent": "",
      "menuParm": "",
      "menuPath": "",
      "menuPerms": "",
      "menuTips": "",
      "menuType": "",
      "pageNum": "",
      "pageSize": "",
      "params": {},
      "remark": "",
      "routeName": "",
      "searchKey": "",
      "sortNo": 0,
      "spellCode": "",
      "startTime": "",
      "terminalCode": "",
      "terminalName": "",
      "updateBy": "",
      "updateTime": "",
      "validFlag": "",
      "visibleFlag": "",
      "wbCode": ""
    }
  ],
  "collected": true,
  "createBy": "",
  "createTime": "",
  "customCode": "",
  "doctorMiniAppMenuType": "",
  "endTime": "",
  "extLink": "",
  "filterMenuCode": "",
  "id": "",
  "keyword": "",
  "menuCode": "",
  "menuCodes": [],
  "menuDesc": "",
  "menuIcon": "",
  "menuName": "",
  "menuParent": "",
  "menuParm": "",
  "menuPath": "",
  "menuPerms": "",
  "menuTips": "",
  "menuType": "",
  "pageNum": "",
  "pageSize": "",
  "params": {},
  "remark": "",
  "routeName": "",
  "searchKey": "",
  "sortNo": 0,
  "spellCode": "",
  "startTime": "",
  "terminalCode": "",
  "terminalName": "",
  "updateBy": "",
  "updateTime": "",
  "validFlag": "",
  "visibleFlag": "",
  "wbCode": ""
}
```


**请求参数**:


| 参数名称 | 参数说明 | 请求类型    | 是否必须 | 数据类型 | schema |
| -------- | -------- | ----- | -------- | -------- | ------ |
|parms|parms|body|true|应用菜单|应用菜单|
|&emsp;&emsp;accessLevel|访问等级||false|string||
|&emsp;&emsp;appCode|应用编码||false|string||
|&emsp;&emsp;appName|应用名称||false|string||
|&emsp;&emsp;appSortNo|||false|integer(int32)||
|&emsp;&emsp;cacheFlag|是否缓存(sys_yesno_flag)||false|string||
|&emsp;&emsp;checked|是否选中||false|boolean||
|&emsp;&emsp;children|||false|array|应用菜单|
|&emsp;&emsp;collected|是否收藏||false|boolean||
|&emsp;&emsp;createBy|创建人||false|string||
|&emsp;&emsp;createTime|创建时间||false|string(date-time)||
|&emsp;&emsp;customCode|自定义编码||false|string||
|&emsp;&emsp;doctorMiniAppMenuType|医务端菜单返回类型||false|string||
|&emsp;&emsp;endTime|查询时间结束||false|string(date-time)||
|&emsp;&emsp;extLink|外部链接||false|string||
|&emsp;&emsp;filterMenuCode|菜单树筛选菜单||false|string||
|&emsp;&emsp;id|主键||false|string||
|&emsp;&emsp;keyword|搜索关键词||false|string||
|&emsp;&emsp;menuCode|菜单编码||false|string||
|&emsp;&emsp;menuCodes|菜单组-用于删除||false|array|string|
|&emsp;&emsp;menuDesc|菜单描述||false|string||
|&emsp;&emsp;menuIcon|菜单图标||false|string||
|&emsp;&emsp;menuName|菜单名称||false|string||
|&emsp;&emsp;menuParent|上级菜单||false|string||
|&emsp;&emsp;menuParm|菜单组件||false|string||
|&emsp;&emsp;menuPath|菜单路由||false|string||
|&emsp;&emsp;menuPerms|权限标识||false|string||
|&emsp;&emsp;menuTips|菜单提示||false|string||
|&emsp;&emsp;menuType|菜单类型(sys_menu_type)||false|string||
|&emsp;&emsp;pageNum|分页参数-当前页数||false|string||
|&emsp;&emsp;pageSize|分页参数-单页显示数||false|string||
|&emsp;&emsp;params|请求参数||false|object||
|&emsp;&emsp;remark|备注||false|string||
|&emsp;&emsp;routeName|||false|string||
|&emsp;&emsp;searchKey|用于模糊搜索拼音码五笔码||false|string||
|&emsp;&emsp;sortNo|排序号||false|integer(int32)||
|&emsp;&emsp;spellCode|拼音首码||false|string||
|&emsp;&emsp;startTime|查询时间开始||false|string(date-time)||
|&emsp;&emsp;terminalCode|终端编码||false|string||
|&emsp;&emsp;terminalName|所属终端名称||false|string||
|&emsp;&emsp;updateBy|修改人||false|string||
|&emsp;&emsp;updateTime|修改时间||false|string(date-time)||
|&emsp;&emsp;validFlag|有效标志||false|string||
|&emsp;&emsp;visibleFlag|是否可见(sys_visible_flag)||false|string||
|&emsp;&emsp;wbCode|五笔首码||false|string||


**响应状态**:


| 状态码 | 说明 | schema |
| -------- | -------- | ----- | 
|200|OK|响应消息体|
|201|Created||
|401|Unauthorized||
|403|Forbidden||
|404|Not Found||


**响应参数**:


| 参数名称 | 参数说明 | 类型 | schema |
| -------- | -------- | ----- |----- | 
|code|状态码：成功标记=1，失败标记=0|string||
|data|数据|object||
|extendInfo|扩展信息|string||
|message|返回信息|string||
|pageNum|页数|integer(int32)|integer(int32)|
|pageSize|页数大小|integer(int32)|integer(int32)|
|timestamp|返回时间|integer(int64)|integer(int64)|
|total|总条数|integer(int64)|integer(int64)|


**响应示例**:
```javascript
{
	"code": "",
	"data": {},
	"extendInfo": "",
	"message": "",
	"pageNum": 0,
	"pageSize": 0,
	"timestamp": 0,
	"total": 0
}
```