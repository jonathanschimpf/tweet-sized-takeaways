from transformers import AutoProcessor, AutoModelForVision2Seq
from PIL import Image
import torch

# ✅ DETECT CPU OR GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
dtype = torch.float16 if device.type == "cuda" else torch.float32

print(f"\n🧠 Loading LLaVA model with dtype={dtype} on device={device}...\n")

# ✅ LOAD LLAVA
processor = AutoProcessor.from_pretrained("llava-hf/llava-1.5-7b-hf")
model = (
    AutoModelForVision2Seq.from_pretrained(
        "llava-hf/llava-1.5-7b-hf",
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    )
    .to(device)
    .eval()
)


def caption_image(img_path: str) -> str:
    # ✅ LOAD AND PREP IMAGE
    raw_image = Image.open(img_path).convert("RGB")
    print(f"\n🖼️ Image shape: {raw_image.size}")

    # ✅ FORMAT PROMPT USING CHAT TEMPLATE
    messages = [
        {
            "role": "user",
            "content": (
                "Describe this image as if you're reading it like a human. "
                "Focus only on visible text. Do NOT describe objects or layout or photos. "
                "Ignore banners, sidebars, or boxes that look like ads. "
                "Only summarize meaningful written content."
            ),
        }
    ]

    # ✅ DEBUG: SHOW TOKEN COUNT FROM CHAT TEMPLATE
    try:
        token_ids = processor.tokenizer.apply_chat_template(
            messages, return_tensors="pt"
        )
        print(f"🧪 Token count: {token_ids.shape[-1]}")
    except Exception as e:
        print(f"⚠️ Tokenizer chat template failed: {e}")

    # ✅ RUN LLaVA GENERATION
    try:
        inputs = processor(images=raw_image, text=messages, return_tensors="pt").to(
            device
        )
        output = model.generate(**inputs, max_new_tokens=100)
        caption = processor.decode(output[0], skip_special_tokens=True)
        return caption
    except Exception as e:
        print("\n❌ LLaVA Captioning Failed:")
        print(e)
        return "[LLaVA failed to generate caption]"
