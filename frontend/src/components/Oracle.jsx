import { useState } from 'react';
import api from '../api/api';
import MemoryCard from './MemoryCard';
import './Oracle.css';

const Oracle = () => {
    const [query, setQuery] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleInquiry = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setError('');
        setLoading(true);
        setResult(null);

        try {
            const data = await api.post('/query', {
                query: query.trim(),
                include_summary: true,
                top_k: 5
            });
            setResult(data);
        } catch (err) {
            console.error('Oracle inquiry failed:', err);
            setError('The Oracle is currently silent. Please try again later.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <section className="oracle-section">
            <form onSubmit={handleInquiry} className="oracle-inquiry">
                <input
                    type="text"
                    className="oracle-input"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Consult the Oracle on..."
                    disabled={loading}
                />
                {loading && <p className="oracle-pondering">pondering...</p>}
            </form>

            {error && <p className="oracle-error">{error}</p>}

            {result && (
                <div className="oracle-synthesis fade-in">
                    <div className="synthesis-divider">
                        <span className="dot-sep">...</span>
                    </div>

                    <article className="synthesis-manuscript">
                        <h3 className="synthesis-title">The Synthesis</h3>
                        <div className="synthesis-body">
                            <p>{result.summary}</p>
                        </div>
                    </article>

                    <footer className="synthesis-references">
                        <h4 className="mono-label">Neurons Engaged</h4>
                        <div className="reference-grid">
                            {result.results && result.results.map((memory) => (
                                <MemoryCard key={memory.id} memory={memory} />
                            ))}
                        </div>
                    </footer>
                </div>
            )}
        </section>
    );
};

export default Oracle;
