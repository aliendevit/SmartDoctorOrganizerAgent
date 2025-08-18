from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="gemma-3/270m-it",      # or the exact repo you use
    revision="main",                # or a specific commit SHA
    local_dir=r"C:\Users\asult\.cache\huggingface\hub\models--gemma-3--270m-it",
    local_dir_use_symlinks=False    # Windows: make real files, not symlinks
)
