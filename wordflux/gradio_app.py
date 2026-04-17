import os
import yaml
import gradio as gr

from wordflux import DocxTranslator


def load_env_file(env_path: str = ".env") -> None:
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def load_config(config_path: str = "config.yaml") -> dict:
    if not os.path.exists(config_path):
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        if isinstance(data, dict):
            return data
    return {}


def translate_docx(
    input_file: str,
    api_key: str,
    model: str,
    source_lang: str,
    target_lang: str,
    max_chunk_size: int,
    max_concurrent: int,
    output_dir: str,
    openai_api_base_url: str,
    progress=gr.Progress(track_tqdm=True),
):
    try:
        if not input_file:
            return "Vui lòng chọn file .docx", None

        effective_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not effective_api_key:
            return "Thiếu OPENAI_API_KEY. Hãy nhập trực tiếp hoặc đặt trong .env", None

        progress(0.05, desc="Đang khởi tạo...")
        final_output_dir = output_dir.strip() if output_dir else "output"

        translator = DocxTranslator(
            input_file=input_file,
            output_dir=final_output_dir,
            openai_api_key=effective_api_key,
            model=model.strip() if model else "gpt-4o-mini",
            source_lang=source_lang.strip() if source_lang else "English",
            target_lang=target_lang.strip() if target_lang else "Vietnamese",
            max_chunk_size=int(max_chunk_size),
            max_concurrent=int(max_concurrent),
            base_url=openai_api_base_url.strip() if openai_api_base_url else None,
        )

        progress(0.2, desc="Đang trích xuất nội dung từ DOCX...")
        translator.extract()

        progress(0.35, desc="Đang dịch nội dung qua OpenAI...")
        translator.translator.translate()

        progress(0.9, desc="Đang ghép nội dung vào file kết quả...")
        translator.inject()

        progress(1.0, desc="Hoàn tất")
        output_path = translator.get_output_path()
        return f"Hoàn tất: {output_path}", output_path
    except Exception as e:
        return f"Lỗi: {e}", None


def build_app() -> gr.Blocks:
    load_env_file(".env")
    config = load_config("config.yaml")

    default_model = config.get("model", "gpt-4o-mini")
    default_source_lang = config.get("source_lang", "English")
    default_target_lang = config.get("target_lang", "Vietnamese")
    default_max_chunk_size = int(config.get("max_chunk_size", 5000))
    default_max_concurrent = int(config.get("max_concurrent", 100))
    default_base_url = config.get("openai_api_base_url", "")

    language_choices = [
        "English",
        "Vietnamese",
        "Chinese",
        "Japanese",
        "Korean",
    ]
    if default_source_lang not in language_choices:
        language_choices.append(default_source_lang)
    if default_target_lang not in language_choices:
        language_choices.append(default_target_lang)

    with gr.Blocks(title="WordFlux - Giao diện dịch tài liệu") as app:
        gr.Markdown("# Giao diện WordFlux\nDịch DOCX nhanh bằng OpenAI, giữ nguyên định dạng")

        with gr.Row():
            with gr.Column(scale=2):
                input_file = gr.File(label="Tệp DOCX đầu vào", file_types=[".docx"], type="filepath")
                output_dir = gr.Textbox(label="Thư mục đầu ra (output_dir)", value="output")
                api_key = gr.Textbox(label="Khóa OPENAI_API_KEY (tuỳ chọn nếu đã có trong .env)", type="password", value="")
                openai_api_base_url = gr.Textbox(label="Địa chỉ OpenAI API (openai_api_base_url)", value=default_base_url)

            with gr.Column(scale=2):
                model = gr.Textbox(label="Mô hình (model)", value=default_model)
                source_lang = gr.Dropdown(label="Ngôn ngữ nguồn (source_lang)", choices=language_choices, value=default_source_lang)
                target_lang = gr.Dropdown(label="Ngôn ngữ đích (target_lang)", choices=language_choices, value=default_target_lang)
                max_chunk_size = gr.Number(label="Kích thước đoạn tối đa (max_chunk_size)", value=default_max_chunk_size, precision=0)
                max_concurrent = gr.Number(label="Số luồng đồng thời (max_concurrent)", value=default_max_concurrent, precision=0)

        run_button = gr.Button("Bắt đầu dịch", variant="primary")
        status_text = gr.Textbox(label="Trạng thái", interactive=False)
        output_file = gr.File(label="Tệp DOCX đã dịch", interactive=False)

        run_button.click(
            fn=translate_docx,
            inputs=[
                input_file,
                api_key,
                model,
                source_lang,
                target_lang,
                max_chunk_size,
                max_concurrent,
                output_dir,
                openai_api_base_url,
            ],
            outputs=[status_text, output_file],
        )

    return app


def main():
    app = build_app()
    app.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
