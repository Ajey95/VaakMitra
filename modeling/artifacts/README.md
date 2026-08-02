# Local model artifacts

Place approved ONNX or ORT model files in this directory for local development. Model files are
ignored by Git. Each model must have a reviewed vocabulary and a JSON manifest containing its
SHA-256 digest, versions, tensor names, sample rate, frame shift, blank index, and output kind.

The repository does not ship a production Tamil phoneme model because the phoneme inventory,
trained phoneme CTC head, licences, and validation evidence require project approval.
