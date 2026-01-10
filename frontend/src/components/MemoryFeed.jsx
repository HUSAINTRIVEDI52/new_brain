import { useState, useEffect } from 'react';
import MemoryCard from './MemoryCard';
import api from '../api/api';
import './MemoryFeed.css';

const MemoryFeed = () => {
    const [memories, setMemories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchMemories();
    }, []);

    const fetchMemories = async () => {
        try {
            setLoading(true);
            // Fetch memories from backend
            // Assuming a GET /memories endpoint exists or we use search with empty query
            const data = await api.get('/memories');
            setMemories(data);
        } catch (err) {
            console.error('Failed to fetch memories:', err);
            setError('The archives could not be reached.');

            // MOCK DATA for initial dev if endpoint isn't ready
            setMemories([
                {
                    id: 1,
                    title: "Spaced Repetition Systems",
                    summary: "Exploring the Ebbinghaus forgetting curve. The core idea is that memory strength decays over time unless reinforced at specific intervals.",
                    created_at: new Date().toISOString(),
                    retention_score: 0.95,
                    is_resurfaced: false
                },
                {
                    id: 2,
                    title: "Neural Plasticity in Adults",
                    summary: "Recent studies show that the adult brain remains remarkably plastic. Learning new skills late in life can physically reshape cortical maps.",
                    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
                    retention_score: 0.42,
                    is_resurfaced: false
                },
                {
                    id: 3,
                    title: "Zettelkasten Method",
                    summary: "A personal tool for thinking and writing. It emphasizes the importance of making connections between atomic notes rather than just storing information.",
                    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
                    retention_score: 0.75,
                    is_resurfaced: true
                }
            ]);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="feed-status">Consulting the archives...</div>;
    if (error) return <div className="feed-status error">{error}</div>;

    return (
        <div className="memory-feed">
            {memories.length === 0 ? (
                <div className="empty-feed">
                    <p>Your library is currently silent. Begin your archive above.</p>
                </div>
            ) : (
                <div className="feed-stack">
                    {memories.map(memory => (
                        <MemoryCard key={memory.id} memory={memory} />
                    ))}
                </div>
            )}
        </div>
    );
};

export default MemoryFeed;
