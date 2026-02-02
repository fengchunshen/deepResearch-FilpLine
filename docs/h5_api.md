# H5 移动端 API 接口文档

## 概述

- **模块**: H5 移动端服务
- **认证方式**: 所有接口需要在请求头中携带 API Key

---

## 接口列表

| 序号 | 方法 | 路径 | 功能 |
|------|------|------|------|
| 1 | GET | /health | 健康检查 |
| 2 | POST | /policy/interpret/stream | 政策解读（流式） |
| 3 | POST | /company/query/simple | 企业简单查询 |
| 4 | GET | /tianyancha/search | 天眼查企业搜索 |
| 5 | GET | /tianyancha/baseinfo | 天眼查企业基本信息 |
| 6 | GET | /tianyancha/patents | 天眼查企业专利 |
| 7 | GET | /tianyancha/certificates | 天眼查企业资质证书 |

---

## 接口详情

### 1. 健康检查

| 项目 | 内容 |
|------|------|
| **路径** | `GET /health` |
| **描述** | H5 移动端服务健康检查 |

**响应示例**:

```json
{
  "status": "healthy",
  "service": "h5"
}
```

---

### 2. 政策解读（流式）

| 项目 | 内容 |
|------|------|
| **路径** | `POST /policy/interpret/stream` |
| **描述** | 调用 FastGPT 进行政策解读，返回 SSE 流式响应 |

**请求参数** (JSON Body):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| policy_name | string | 是 | 政策名称 |
| chat_id | string | 否 | 会话 ID |

**请求示例**:

```json
{
  "policy_name": "高新技术企业认定管理办法",
  "chat_id": "abc123"
}
```

**响应**: `text/event-stream` SSE 流式响应

---

### 3. 企业简单查询

| 项目 | 内容 |
|------|------|
| **路径** | `POST /company/query/simple` |
| **描述** | 根据企业信息查询相关政策文件 |

**请求参数** (JSON Body):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| companyName | string | 是 | 企业名称 |
| companyScale | string | 否 | 企业规模 |
| companyCategory | string[] | 否 | 企业类别列表 |
| industry | string | 否 | 行业 |
| revenueLastYear | any | 否 | 去年营收 |
| businessScope | string | 否 | 经营范围 |
| otherInformation | string | 否 | 其他信息 |

**请求示例**:

```json
{
  "companyName": "XX科技有限公司",
  "companyScale": "中型企业",
  "companyCategory": ["高新技术企业"],
  "industry": "软件和信息技术服务业"
}
```

---

### 4. 天眼查企业搜索

| 项目 | 内容 |
|------|------|
| **路径** | `GET /tianyancha/search` |
| **描述** | 通过关键词搜索企业列表 |

**请求参数** (Query):

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| word | string | 是 | - | 搜索关键词 |
| pageSize | int | 否 | 20 | 每页条数，最大 20 |
| pageNum | int | 否 | 1 | 当前页数 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| total | int | 总数 |
| items | array | 企业列表 |
| items[].id | int | 公司 ID |
| items[].name | string | 公司名称 |
| items[].type | int | 类型 |
| items[].companyType | int | 公司类型 |
| items[].base | string | 所在地 |
| items[].legalPersonName | string | 法人代表 |
| items[].regCapital | string | 注册资本 |
| items[].estiblishTime | string | 成立日期 |
| items[].regStatus | string | 经营状态 |
| items[].creditCode | string | 统一社会信用代码 |
| items[].regNumber | string | 注册号 |
| items[].orgNumber | string | 组织机构代码 |
| items[].matchType | string | 匹配类型 |

---

### 5. 天眼查企业基本信息

| 项目 | 内容 |
|------|------|
| **路径** | `GET /tianyancha/baseinfo` |
| **描述** | 通过公司名称或 ID 获取企业基本信息 |

**请求参数** (Query):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 是 | 公司名称、公司 ID、注册号或统一社会信用代码 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 公司 ID |
| name | string | 公司名称 |
| type | int | 类型 |
| companyOrgType | string | 企业类型 |
| estiblishTime | string | 成立日期 |
| regStatus | string | 经营状态 |
| regCapital | string | 注册资本 |
| legalPersonName | string | 法人代表 |
| regNumber | string | 工商注册号 |
| creditCode | string | 统一社会信用代码 |
| orgNumber | string | 组织机构代码 |
| taxNumber | string | 纳税人识别号 |
| regLocation | string | 注册地址 |
| regInstitute | string | 登记机关 |
| businessScope | string | 经营范围 |
| industry | string | 行业 |
| staffNumRange | string | 人员规模 |
| socialStaffNum | int | 参保人数 |
| base | string | 省份简称 |
| city | string | 城市 |
| district | string | 区县 |
| approvedTime | string | 核准日期 |
| historyNames | string | 曾用名 |
| bondName | string | 股票名称 |
| bondNum | string | 股票号 |
| bondType | string | 股票类型 |
| actualCapital | string | 实缴资本 |

---

### 6. 天眼查企业专利信息

| 项目 | 内容 |
|------|------|
| **路径** | `GET /tianyancha/patents` |
| **描述** | 通过公司名称或 ID 获取专利信息 |

**请求参数** (Query):

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| keyword | string | 是 | - | 公司名称、公司 ID、注册号或统一社会信用代码 |
| pageSize | int | 否 | 20 | 每页条数，最大 20 |
| pageNum | int | 否 | 1 | 当前页数 |
| patentType | int | 否 | - | 专利类型：1-发明专利 2-实用新型 3-外观专利 |
| appDateBegin | string | 否 | - | 申请开始时间 (YYYY-MM-DD) |
| appDateEnd | string | 否 | - | 申请结束时间 (YYYY-MM-DD) |
| pubDateBegin | string | 否 | - | 发布开始时间 (YYYY-MM-DD) |
| pubDateEnd | string | 否 | - | 发布结束时间 (YYYY-MM-DD) |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| total | int | 总数 |
| items | array | 专利列表 |
| items[].id | int | 专利 ID |
| items[].patentName | string | 专利名称 |
| items[].patentNum | string | 申请号 |
| items[].applicationPublishNum | string | 申请公布号 |
| items[].patentType | string | 专利类型 |
| items[].patentStatus | string | 专利状态 |
| items[].applicationTime | string | 申请日期 |
| items[].pubDate | string | 公布日期 |
| items[].applicantname | string | 申请人 |
| items[].inventor | string | 发明人 |
| items[].agent | string | 代理人 |
| items[].agency | string | 代理机构 |
| items[].address | string | 地址 |
| items[].abstracts | string | 摘要 |
| items[].mainCatNum | string | 主分类号 |
| items[].cat | string | 分类 |

---

### 7. 天眼查企业资质证书

| 项目 | 内容 |
|------|------|
| **路径** | `GET /tianyancha/certificates` |
| **描述** | 通过公司名称或 ID 获取资质证书信息 |

**请求参数** (Query):

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| name | string | 否* | - | 公司名称 |
| id | int | 否* | - | 公司 ID |
| certificateName | string | 否 | - | 证书类型 |
| pageSize | int | 否 | 20 | 每页条数，最大 20 |
| pageNum | int | 否 | 1 | 当前页数 |

> **注意**: name 与 id 至少需要提供一个

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| total | int | 总数 |
| items | array | 证书列表 |
| items[].id | string | 证书 ID |
| items[].certNo | string | 证书编号 |
| items[].certificateName | string | 证书名称 |
| items[].certificateType | string | 证书类型 |
| items[].startDate | string | 发证日期 |
| items[].endDate | string | 到期日期 |
| items[].detail | array | 详情列表 |
| items[].detail[].title | string | 标题 |
| items[].detail[].content | string | 内容 |

---

## 错误响应

所有接口在发生错误时返回统一格式：

```json
{
  "detail": "错误描述信息"
}
```

常见 HTTP 状态码：

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权（API Key 无效） |
| 500 | 服务器内部错误 |
