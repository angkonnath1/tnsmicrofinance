import os
import re
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
BACKUP_DIR = os.path.join(BASE_DIR, 'templates_backup_with_icons')
CSS_FILE = os.path.join(BASE_DIR, 'static', 'css', 'style.css')
CSS_BACKUP = os.path.join(BASE_DIR, 'static', 'css', 'style.css.with_icons_backup')

def ensure_backup():
    if not os.path.exists(BACKUP_DIR):
        print("Creating backup of templates in:", BACKUP_DIR)
        shutil.copytree(TEMPLATES_DIR, BACKUP_DIR)
    if not os.path.exists(CSS_BACKUP) and os.path.exists(CSS_FILE):
        print("Creating backup of CSS in:", CSS_BACKUP)
        shutil.copy2(CSS_FILE, CSS_BACKUP)

def remove_icons():
    ensure_backup()
    svg_regex = re.compile(r'<svg[\s\S]*?</svg>', re.IGNORECASE)
    emojis = ['💰', '💳', '👤', '🖨️', '🖨', '📄', '\U0001f4b0', '\U0001f4b3', '\U0001f464', '\U0001f5a8\ufe0f', '\U0001f5a8', '\U0001f4c4']
    total_svg_removed = 0
    modified_files = 0

    for root, dirs, files in os.walk(TEMPLATES_DIR):
        for file in files:
            if not file.endswith('.html'):
                continue
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original = content
            matches = list(svg_regex.finditer(content))
            total_svg_removed += len(matches)

            # 1. Base header controls
            if file == 'base.html':
                content = re.sub(
                    r'<button[^>]*id="sidebar-close-btn"[^>]*>[\s\S]*?</button>',
                    '<button type="button" class="btn btn-sm btn-secondary sidebar-close-btn" id="sidebar-close-btn" onclick="window.closeSidebar(event)" aria-label="Close Sidebar" title="Close Menu (Esc)">Close</button>',
                    content,
                    flags=re.IGNORECASE
                )

                content = re.sub(
                    r'<a href="{% url \'notifications:list\' %}"[^>]*title="Notifications">[\s\S]*?</a>',
                    """<a href="{% url 'notifications:list' %}" class="btn btn-sm btn-secondary" style="position: relative; display: inline-flex; align-items: center; gap: 6px; font-size: 0.82rem; font-weight: 600; text-decoration: none;" title="Notifications">
            Notifications
            {% if unread_notifications_count > 0 %}
            <span style="background: #ef4444; color: #ffffff; border-radius: 9999px; font-size: 0.65rem; font-weight: 800; min-width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; padding: 0 4px;">{{ unread_notifications_count }}</span>
            {% endif %}
          </a>""",
                    content
                )

            # 2. Photo preview boxes
            if file in ['member_create.html', 'register.html']:
                content = re.sub(
                    r'(<div[^>]*class="photo-preview-box"[^>]*>)\s*<svg[\s\S]*?</svg>\s*(</div>)',
                    r'\1<span style="font-size: 0.75rem; color: #94a3b8;">No Photo</span>\2',
                    content,
                    flags=re.IGNORECASE
                )

            # 3. Strip SVGs
            content = svg_regex.sub('', content)

            # 3b. Add back the 3-bar hamburger icon specifically to #sidebar-toggle-btn in base.html
            if file == 'base.html':
                content = re.sub(
                    r'<button[^>]*id="sidebar-toggle-btn"[^>]*>[\s\S]*?</button>',
                    '<button type="button" class="btn-hamburger" id="sidebar-toggle-btn" onclick="window.toggleSidebar(event)" aria-label="Toggle Navigation Menu" title="Open Menu (3-Bar)"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 22px; height: 22px; pointer-events: none;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M4 6h16M4 12h16M4 18h16" /></svg></button>',
                    content,
                    flags=re.IGNORECASE
                )
                content = re.sub(
                    r'<button[^>]*id="sidebar-close-btn"[^>]*>[\s\S]*?</button>',
                    '<button type="button" class="sidebar-close-btn" id="sidebar-close-btn" onclick="window.closeSidebar(event)" aria-label="Close Sidebar" title="Close Menu (Esc)"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 18px; height: 18px; pointer-events: none;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M6 18L18 6M6 6l12 12" /></svg></button>',
                    content,
                    flags=re.IGNORECASE
                )

            # 4. Strip button emojis
            for emo in emojis:
                content = content.replace(emo + ' ', '')
                content = content.replace(emo, '')

            # 5. Remove checkmarks & cross symbols
            content = re.sub(r'(&check;|[\u2713\u2714])\s*', '', content)
            content = re.sub(r'([\u2715\u2716])\s*Reject Application', 'Reject Application', content)
            content = re.sub(r'&times;\s*Reject Application', 'Reject Application', content)

            # 6. Modal close buttons & search clear buttons
            content = re.sub(
                r'(<button\b[^>]*class="[^"]*btn-sm btn-secondary[^"]*"[^>]*onclick="closeModal\([^)]+\)"[^>]*>)\s*&times;\s*(</button>)',
                r'\1Close\2',
                content
            )
            content = re.sub(
                r'(<button\b[^>]*class="member-search-clear"[^>]*>)\s*&times;\s*(</button>)',
                r'\1Clear\2',
                content
            )
            content = re.sub(
                r'(<button\b[^>]*id="clear(?:Loan|Member)Search"[^>]*>)\s*[\u2715\u2716&times;]+\s*(</button>)',
                r'\1Clear\2',
                content
            )

            # 7. Strip arrows (&rarr;, &larr;, etc.)
            content = re.sub(r'\s*(&rarr;|&larr;|→|←)\s*', ' ', content)

            # 8. Pagination arrows
            if file == 'pagination.html':
                content = content.replace('&laquo; First', 'First')
                content = content.replace('&lsaquo; Prev', 'Prev')
                content = content.replace('Next &rsaquo;', 'Next')
                content = content.replace('Last &raquo;', 'Last')

            # Clean empty stat icon wrap
            content = re.sub(r'<div class="stat-icon-wrap[^"]*">\s*</div>\s*', '', content)

            if content != original:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                modified_files += 1

    # Update CSS
    if os.path.exists(CSS_FILE):
        with open(CSS_FILE, 'r', encoding='utf-8') as f:
            css_content = f.read()
        css_addition = "\n/* --- ICONS REMOVED ADJUSTMENTS --- */\n.stat-icon-wrap { display: none !important; }\n.btn-icon-bell { width: auto !important; padding: 0 12px !important; gap: 6px !important; }\n"
        if "/* --- ICONS REMOVED ADJUSTMENTS --- */" not in css_content:
            with open(CSS_FILE, 'a', encoding='utf-8') as f:
                f.write(css_addition)

    print(f"\n[DONE] Successfully removed all SVG icons and button icons across {modified_files} template files.")
    print("All originals are safely stored in 'templates_backup_with_icons'.")
    print("To restore all icons, run: python manage_icons.py restore")

def restore_icons():
    if not os.path.exists(BACKUP_DIR):
        print(f"[ERROR] Backup directory '{BACKUP_DIR}' not found! Cannot restore.")
        return

    print("Restoring all template files from backup...")
    shutil.rmtree(TEMPLATES_DIR)
    shutil.copytree(BACKUP_DIR, TEMPLATES_DIR)

    if os.path.exists(CSS_BACKUP):
        shutil.copy2(CSS_BACKUP, CSS_FILE)
        print("Restored style.css from backup.")

    print("\n[DONE] Successfully restored all icons and original button styles from backup!")

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'remove'
    if action == 'remove':
        remove_icons()
    elif action == 'restore':
        restore_icons()
    else:
        print("Usage: python manage_icons.py [remove|restore]")
