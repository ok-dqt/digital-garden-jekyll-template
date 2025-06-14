import os
import re
import shutil
import yaml
import datetime


# 配置路径
OBSIDIAN_NOTES_PATH = './obsidian-vault'
JEKYLL_POSTS_PATH = './blog/_posts'
JEKYLL_NOTES_PATH = './blog/_notes'
JEKYLL_IMAGES_PATH = './blog/assets/images'

def clean_jekyll_output_directories():
    """清空 Jekyll 的 _posts 和 _notes 目录，但不删除目录本身。"""
    for path in [JEKYLL_POSTS_PATH, JEKYLL_NOTES_PATH]:
        if os.path.exists(path):
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
        else:
            os.makedirs(path, exist_ok=True)

def process_note(filepath):
    """处理单个 Obsidian 笔记文件。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取 YAML Front Matter 和内容
    match = re.match(r'---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if not match:
        print(f"Skipping {filepath}: No valid YAML front matter found.")
        return

    yaml_str = match.group(1)
    markdown_content = match.group(2)

    try:
        front_matter = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        print(f"Skipping {filepath}: Invalid YAML front matter - {e}")
        return

    # 检查 publish 标记和 status
    if not front_matter or not front_matter.get('publish') or front_matter.get('status') == 'draft':
        print(f"Skipping {filepath}: 'publish: true' not found or status is draft.")
        return

    # 根据 type 字段分类内容
    note_type = front_matter.get('type', 'note') # 默认为 note
    target_path = JEKYLL_NOTES_PATH if note_type == 'note' else JEKYLL_POSTS_PATH

    print(f"Processing {filepath} as {note_type} for publishing...")



    # 处理内部链接 [[Page Name]] -> {{< ref "page-name" >}}
    # Jekyll 默认的 permalink 结构通常是 /:categories/:year/:month/:day/:title.html
    # 这里我们假设使用 slug 作为 permalink，例如 /notes/:slug
    # 并且内部链接指向的是 Jekyll 网站内部的相对路径
    markdown_content = re.sub(r'\[\[(.*?)\]\]', r'[\1](/notes/\1)', markdown_content)
    markdown_content = re.sub(r'\!\[\[(.*?)\]\]', r'![[\1]]', markdown_content) # 忽略图片链接

    # 处理图片链接 ![[image.jpg]] -> ../assets/images/image.jpg
    # 假设图片都放在 _notes 目录同级或子目录，并最终复制到 assets/images
    def replace_image_path(match):
        image_name = match.group(1)
        # 复制图片到 Jekyll 的 assets/images 目录
        source_image_path = os.path.join(os.path.dirname(filepath), image_name)
        if not os.path.exists(source_image_path):
            # 尝试在 _notes 目录下查找图片
            source_image_path = os.path.join(OBSIDIAN_NOTES_PATH, image_name)
        if not os.path.exists(source_image_path):
            print(f"Warning: Image not found at {source_image_path}")
            return match.group(0) # 返回原始字符串

        os.makedirs(JEKYLL_IMAGES_PATH, exist_ok=True)
        shutil.copy(source_image_path, os.path.join(JEKYLL_IMAGES_PATH, image_name))
        return f"![](/assets/images/{image_name})"

    markdown_content = re.sub(r'!\\[\\[(.*?)\\]\\]', replace_image_path, markdown_content)

    # 生成 Jekyll 友好的文件名 (YYYY-MM-DD-title.md)
    title = front_matter.get('title', os.path.basename(filepath).replace('.md', ''))
    date = front_matter.get('date')
    if not date:
        # 如果没有日期，使用文件修改日期或当前日期
        date = datetime.datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d')
    else:
        date = date.strftime('%Y-%m-%d') if isinstance(date, datetime.date) else date

    # 将标题转换为 slug
    slug = re.sub(r'[^a-zA-Z0-9\-]+', '', title).lower().strip('-')
    slug = re.sub(r'\s+', '-', slug)
    filename = f"{date}-{slug}.md"
    output_filepath = os.path.join(target_path, filename)

    # 重新构建 Front Matter
    front_matter['layout'] = front_matter.get('layout', 'post') # 默认布局为 post
    front_matter['title'] = title
    front_matter['date'] = date

    new_yaml_str = yaml.dump(front_matter, allow_unicode=True, sort_keys=False)
    new_content = f"---\n{new_yaml_str}---\n{markdown_content}"

    # 写入新文件
    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Generated filename: {filename}")
    print(f"Successfully published {filepath} to {output_filepath}")

def main():
    clean_jekyll_output_directories()
    for root, _, files in os.walk(OBSIDIAN_NOTES_PATH):
        for file in files:
            if file.endswith('.md'):
                process_note(os.path.join(root, file))

if __name__ == '__main__':
    main()