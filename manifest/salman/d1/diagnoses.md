# Three Refusal Diagnoses

- pod-a: ImagePullBackOff — the node/kubelet could not pull the image because the tag does not exist.
- pod-b: Pending — the scheduler refused it because the node has insufficient CPU.
- pod-c: CrashLoop/Error — the container started and exited with code 3, so the container itself failed.