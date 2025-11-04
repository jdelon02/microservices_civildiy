import React from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Image from '@tiptap/extension-image';
import './RichTextEditor.css';

const RichTextEditor = ({ value, onChange, placeholder = 'Write your content here...' }) => {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        paragraph: {
          HTMLAttributes: {
            class: 'editor-paragraph',
          },
        },
      }),
      Image.configure({
        HTMLAttributes: {
          class: 'editor-image',
        },
      }),
    ],
    content: value || '',
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
  });

  if (!editor) {
    return null;
  }

  const addImage = () => {
    const url = window.prompt('Enter image URL:');
    if (url) {
      editor.chain().focus().setImage({ src: url }).run();
    }
  };

  return (
    <div className="rich-text-editor">
      <div className="editor-toolbar">
        <button
          onClick={() => editor.chain().focus().toggleBold().run()}
          disabled={!editor.can().chain().focus().toggleBold().run()}
          className={editor.isActive('bold') ? 'toolbar-btn active' : 'toolbar-btn'}
          title="Bold (Ctrl+B)"
        >
          <strong>B</strong>
        </button>
        <button
          onClick={() => editor.chain().focus().toggleItalic().run()}
          disabled={!editor.can().chain().focus().toggleItalic().run()}
          className={editor.isActive('italic') ? 'toolbar-btn active' : 'toolbar-btn'}
          title="Italic (Ctrl+I)"
        >
          <em>I</em>
        </button>
        <button
          onClick={() => editor.chain().focus().toggleStrike().run()}
          disabled={!editor.can().chain().focus().toggleStrike().run()}
          className={editor.isActive('strike') ? 'toolbar-btn active' : 'toolbar-btn'}
          title="Strikethrough"
        >
          <s>S</s>
        </button>

        <div className="toolbar-divider" />

        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          className={editor.isActive('heading', { level: 1 }) ? 'toolbar-btn active' : 'toolbar-btn'}
          title="Heading 1"
        >
          H1
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={editor.isActive('heading', { level: 2 }) ? 'toolbar-btn active' : 'toolbar-btn'}
          title="Heading 2"
        >
          H2
        </button>
        <button
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={editor.isActive('bulletList') ? 'toolbar-btn active' : 'toolbar-btn'}
          title="Bullet List"
        >
          •
        </button>
        <button
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={editor.isActive('orderedList') ? 'toolbar-btn active' : 'toolbar-btn'}
          title="Ordered List"
        >
          1.
        </button>

        <div className="toolbar-divider" />

        <button
          onClick={addImage}
          className="toolbar-btn"
          title="Add Image"
        >
          🖼️
        </button>
        <button
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          className={editor.isActive('codeBlock') ? 'toolbar-btn active' : 'toolbar-btn'}
          title="Code Block"
        >
          &lt;/&gt;
        </button>

        <div className="toolbar-divider" />

        <button
          onClick={() => editor.chain().focus().setHorizontalRule().run()}
          className="toolbar-btn"
          title="Horizontal Rule"
        >
          ━
        </button>
        <button
          onClick={() => editor.chain().focus().clearNodes().run()}
          className="toolbar-btn"
          title="Clear Formatting"
        >
          ✕
        </button>
      </div>

      <EditorContent editor={editor} className="editor-content" />
      <div className="editor-placeholder">{!value && placeholder}</div>
    </div>
  );
};

export default RichTextEditor;
