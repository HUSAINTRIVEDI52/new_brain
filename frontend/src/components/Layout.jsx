import './Layout.css';

const Layout = ({ children, onLogout, userEmail }) => {
    return (
        <div className="layout-root">
            {/* Subtle Left Sidebar (The Archives) */}
            <aside className="sidebar-archives">
                <nav className="sidebar-nav">
                    <span className="sidebar-label"># ARCHIVES</span>
                    <ul className="sidebar-list">
                        <li>Reflections</li>
                        <li>Neural Notes</li>
                        <li>Daily Log</li>
                        <li>Timeless</li>
                    </ul>
                </nav>
            </aside>

            {/* Main Perspective */}
            <div className="main-perspective">
                {/* The Promenade (Header) */}
                <header className="promenade">
                    <div className="header-left">
                        <h1 className="header-logo">Second Brain</h1>
                    </div>
                    <div className="header-right">
                        <button className="button-ink" title="New Memory">+</button>
                        <button className="button-ink" title="Search">Search</button>
                        <button className="button-ink close-btn" onClick={onLogout}>Close Archive</button>
                    </div>
                </header>

                {/* Content Area (The Manuscript) */}
                <main className="content-manuscript">
                    {children}
                </main>

                <footer className="manuscript-footer">
                    <hr className="faint-hr" />
                    <p className="footer-note">Handcrafted for the thoughtful. | {userEmail}</p>
                </footer>
            </div>
        </div>
    );
};

export default Layout;
