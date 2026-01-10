import { useState, useEffect } from 'react';
import api from '../api/api';
import './Chronology.css';

const Chronology = () => {
    const [groups, setGroups] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchAndGroupMemories();
    }, []);

    const fetchAndGroupMemories = async () => {
        try {
            setLoading(true);
            const memories = await api.get('/memories');

            const grouped = groupMemories(memories);
            setGroups(grouped);
        } catch (err) {
            console.error('Failed to fetch chronology:', err);
            setError('The scrolls of time could not be unrolled.');

            // MOCK DATA for initial dev
            const mockMemories = [
                { id: 1, summary: 'Finished reading "The Paper Menagerie". A profound collection of stories.', created_at: '2023-11-12T10:00:00Z' },
                { id: 2, summary: 'Idea for a new project: "Whispering Archives". Explored local history museum.', created_at: '2023-11-15T14:30:00Z' },
                { id: 3, summary: 'Coffee with Sarah at "The Daily Grind". Discussed the ethics of memory.', created_at: '2023-11-20T16:00:00Z' },
                { id: 4, summary: 'Drafted the first chapter of my book. The words flowed unexpectedly.', created_at: '2023-11-27T09:00:00Z' },
                { id: 5, summary: 'Observations on neural plasticity and the Ebbinghaus curve.', created_at: '2023-10-12T11:00:00Z' },
                { id: 6, summary: 'Initial thoughts on "Bookbinder" design system.', created_at: '2022-12-05T15:00:00Z' }
            ];
            setGroups(groupMemories(mockMemories));
        } finally {
            setLoading(false);
        }
    };

    const groupMemories = (memories) => {
        const sorted = [...memories].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        const yearGroups = {};

        sorted.forEach(memory => {
            const date = new Date(memory.created_at);
            const year = date.getFullYear();
            const month = date.toLocaleString('default', { month: 'long' });
            const day = date.toLocaleString('default', { month: 'short', day: 'numeric' }).toUpperCase();

            if (!yearGroups[year]) yearGroups[year] = {};
            if (!yearGroups[year][month]) yearGroups[year][month] = [];

            yearGroups[year][month].push({ ...memory, dayLabel: day });
        });

        return Object.entries(yearGroups).sort(([ya], [yb]) => yb - ya).map(([year, months]) => ({
            year,
            months: Object.entries(months).map(([month, items]) => ({ month, items }))
        }));
    };

    if (loading) return <div className="chronology-status">Consulting the scrolls...</div>;
    if (error) return <div className="chronology-status error">{error}</div>;

    return (
        <div className="chronology-view fade-in">
            {groups.map(year => (
                <section key={year.year} className="year-section">
                    <h2 className="year-header">{year.year}</h2>

                    {year.months.map(month => (
                        <div key={month.month} className="month-group">
                            <h3 className="month-label">{month.month}</h3>

                            <div className="timeline-items">
                                {month.items.map(item => (
                                    <div key={item.id} className="timeline-item">
                                        <div className="item-anchor">
                                            <span className="day-mono">{item.dayLabel}</span>
                                        </div>
                                        <div className="item-content">
                                            <p className="item-summary">{item.summary}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </section>
            ))}
        </div>
    );
};

export default Chronology;
