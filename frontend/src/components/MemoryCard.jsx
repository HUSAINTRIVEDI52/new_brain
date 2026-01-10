import './MemoryCard.css';

const MemoryCard = ({ memory }) => {
    const { summary, title, created_at, retention_score, is_resurfaced } = memory;

    // Visual state based on retention
    const isFading = retention_score < 0.5;
    const isStrong = retention_score > 0.8;

    const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    };

    return (
        <div className={`memory-card ${isFading ? 'fading' : ''} ${is_resurfaced ? 'resurfaced' : ''} ${isStrong ? 'strong' : ''}`}>
            {is_resurfaced && <div className="resurfaced-tag">RESURFACED</div>}

            <header className="card-header">
                {title ? (
                    <h3 className="card-title">{title}</h3>
                ) : (
                    <span className="card-date-mono">{formatDate(created_at)}</span>
                )}
            </header>

            <div className="card-body">
                <p className="card-summary">{summary}</p>
            </div>

            <footer className="card-footer">
                {title && <span className="card-date-mono">{formatDate(created_at)}</span>}
                <span className="card-strength-mono">
                    STRENGTH: {Math.round(retention_score * 100)}%
                </span>
            </footer>
        </div>
    );
};

export default MemoryCard;
