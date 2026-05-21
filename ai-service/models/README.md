# Models

Place detector and recognition model files here for local development.

MVP detection scope is person-only. Generic object detection is not enabled in the first release.

Default detector path:

```text
/app/models/yolo-person.pt
```

For local development with the repository mounted directly:

```text
ai-service/models/yolo-person.pt
```

The YOLO adapter lazy-loads the model on first inference, so `/ai/health` can run before a model file is present.
