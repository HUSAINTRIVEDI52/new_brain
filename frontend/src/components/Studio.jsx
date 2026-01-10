import { useState, useRef, useEffect } from 'react';
import api from '../api/api';
import './Studio.css';

const Studio = ({ onEntrySaved }) => {
    const [content, setContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [isFocused, setIsFocused] = useState(false);
    const textareaRef = useRef(null);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
        }
    }, [content]);

    const handleCommit = async () => {
        if (!content.trim()) return;

        setLoading(true);
        try {
            await api.post('/upload', { content: content.trim() });
            setContent('');
            if (onEntrySaved) onEntrySaved();
        } catch (err) {
            console.error('Failed to bind manuscript:', err);
        } finally {
            setLoading(false);
        }
    };

    const inkLevel = Math.min((content.length / 500) * 100, 100);

    return (
        <div className={`studio-container ${isFocused ? 'focus-mode' : ''}`}>
            <textarea
                ref={textareaRef}
                className="studio-textarea"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                placeholder="Commit a thought to ink..."
                rows={1}
            />

            <div className="studio-footer">
                <div className="ink-well">
                    <div
                        className="ink-level"
                        style={{
                            width: `${inkLevel}%`,
                            backgroundColor: inkLevel > 80 ? 'var(--burnt-sienna)' : 'var(--ink-subtle)'
                        }}
                    />
                </div>

                <button
                    className="button-primary seal-button"
                    onClick={handleCommit}
                    disabled={loading || !content.trim()}
                >
                    {loading ? 'Binding...' : 'Bind to Manuscript'}
                </button>
            </div>
        </div>
    );
};

export default Studio;
