# ATDD-M7-Album-AC: 时光相册验收标准

> **对应 TDS**: `docs/architecture/TDS/SPEC-M7-time-album.md`
> **版本**: V1.0
> **状态**: Draft

---

## Feature: 时光相册基础功能

### Background

```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户进入时光相册页面
```

### Scenario: 用户上传 1 张照片 ≤ 5 步

```gherkin
Given 用户进入时光相册页
When 用户点击"上传照片"
And 选择照片（≤ 5 步）
Then 照片上传成功
And 返回 photo_id
And POST /album/photos 返回 201
```

### Scenario: 时间轴按上传时间倒序

```gherkin
Given 用户已上传多张照片
When 用户查看时光相册
Then 照片按上传时间倒序排列
And 最新照片在最前面
And GET /album/photos 返回 photos 按 created_at DESC
```

### Scenario: 用户可删除照片

```gherkin
Given 用户查看时光相册
When 用户点击照片的删除按钮
Then 照片被删除
And DELETE /album/photos/{id} 返回 200
And 用户可重新上传
```

### Scenario: 用户可重新上传照片

```gherkin
Given 用户已删除照片
When 用户点击重新上传
Then 用户可重新选择照片上传
And POST /album/photos 重新返回 201
```

---

## Feature: 隐私设置

### Background

```gherkin
Background:
  Given 用户已登录并持有有效 JWT
  And 用户进入时光相册页面
```

### Scenario: 设置照片为私密

```gherkin
Given 用户上传照片
When 用户设置隐私为"私密"
Then 照片仅自己可见
And PUT /album/photos/{id} 更新 privacy='private'
And 照片不出现在成长广场
```

### Scenario: 设置照片为公开

```gherkin
Given 用户上传照片
When 用户设置隐私为"公开"
Then 照片对所有人可见
And PUT /album/photos/{id} 更新 privacy='public'
And 照片可出现在成长广场（用户选择后）
```

### Scenario: 用户可修改隐私设置

```gherkin
Given 用户已上传照片
When 用户修改隐私设置
Then 设置立即生效
And 广场展示状态同步更新
And GET /album/photos/{id} 返回更新后的 privacy
```

---

## Feature: 合规约束

### Scenario: 不使用 AI 对比

```gherkin
Given 用户查看时光相册
Then 系统不提供任何 AI 对比功能
And 不展示任何雷达图
And 不出现任何照片对比功能
```

### Scenario: 不使用滑动手势

```gherkin
Given 用户查看时光相册
Then 时间轴不使用滑动手势
And 采用点击查看详情模式
And 不使用 swipe / slide / flick 手势
```

### Scenario: 不出现颜值打分

```gherkin
Given 用户查看时光相册
Then 任何界面不出现颜值打分
And 不出现任何评分机制
And 不出现分数/排名/对比数据
```

---

## Feature: 数据复用与字段

### Scenario: 时光相册复用 post 表

```gherkin
Given 用户上传时光相册照片
When POST /album/photos is called
Then photo is stored in post table with album_type='photo'
And post.status is set to 'approved'
And photo_id is independent from post.id
```

### Scenario: day 字段正确关联方案进度

```gherkin
Given 用户已完成 day-N 打卡
When 用户上传时光相册照片
Then photo includes day field indicating plan day
And day is provided by plan service
And day is between 1 and 21
```
