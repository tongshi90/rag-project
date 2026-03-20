import { useState } from 'react';
import { HomePage } from './components/HomePage';
import { HomePageDemo } from './components/HomePageDemo';
import { HomePageDemo2 } from './components/HomePageDemo2';
import { HomePageDemo3 } from './components/HomePageDemo3';
import { SkillListPage } from './components/SkillListPage';
import { SkillFileListPage } from './components/SkillFileListPage';
import { KnowledgeBaseListPage } from './components/KnowledgeBaseListPage';
import { KnowledgeBaseDetailPage } from './components/KnowledgeBaseDetailPage';
import type { SkillCard, KnowledgeBase } from './types';
import './index.css';

type PageType = 'home' | 'skill' | 'skill-files' | 'knowledge-base' | 'knowledge-base-detail';
type ThemeType = 'neon-grid' | 'neon-void' | 'abyss-grid' | 'bg-preview';

// Background type for BG Preview
type BgType = 'cybergrid' | 'starfield' | 'gradientmesh' | 'particles' | 'hexagons' | 'waves' | 'geometric' | 'noise' | 'orbs' | 'circuit' | 'dotmatrix';

// Background renderer component
interface GlobalBackgroundProps {
  theme: ThemeType;
  bgType: BgType;
}

const GlobalBackground: React.FC<GlobalBackgroundProps> = ({ theme, bgType }) => {
  if (theme === 'bg-preview') {
    // Render specific background type
    switch (bgType) {
      case 'cybergrid':
        return (
          <div className="global-bg global-bg-cybergrid">
            <div className="grid-plane">
              {[...Array(20)].map((_, i) => (
                <div key={`h-${i}`} className="grid-line-h" style={{ '--y': `${i * 5}%` } as React.CSSProperties}></div>
              ))}
              {[...Array(20)].map((_, i) => (
                <div key={`v-${i}`} className="grid-line-v" style={{ '--x': `${i * 5}%` } as React.CSSProperties}></div>
              ))}
            </div>
            <div className="grid-glow"></div>
          </div>
        );

      case 'starfield':
        return (
          <div className="global-bg global-bg-starfield">
            {[...Array(80)].map((_, i) => (
              <div
                key={i}
                className="star-point"
                style={{
                  '--x': `${Math.random() * 100}%`,
                  '--y': `${Math.random() * 100}%`,
                  '--size': `${1 + Math.random() * 2}px`,
                  '--delay': `${Math.random() * 3}s`,
                  '--duration': `${2 + Math.random() * 3}s`,
                } as React.CSSProperties}
              ></div>
            ))}
          </div>
        );

      case 'gradientmesh':
        return (
          <div className="global-bg global-bg-gradientmesh">
            <div className="mesh-gradient mesh-1"></div>
            <div className="mesh-gradient mesh-2"></div>
            <div className="mesh-gradient mesh-3"></div>
            <div className="mesh-gradient mesh-4"></div>
          </div>
        );

      case 'particles':
        return (
          <div className="global-bg global-bg-particles">
            {[...Array(30)].map((_, i) => (
              <div
                key={i}
                className="float-particle"
                style={{
                  '--x': `${Math.random() * 100}%`,
                  '--y': `${Math.random() * 100}%`,
                  '--size': `${2 + Math.random() * 3}px`,
                  '--delay': `${Math.random() * 5}s`,
                  '--duration': `${8 + Math.random() * 4}s`,
                } as React.CSSProperties}
              ></div>
            ))}
          </div>
        );

      case 'hexagons':
        return (
          <div className="global-bg global-bg-hexagons">
            {[...Array(15)].map((_, i) => (
              <div
                key={i}
                className="hex-outline"
                style={{
                  '--x': `${(i % 5) * 25}%`,
                  '--y': `${Math.floor(i / 5) * 25}%`,
                  '--delay': `${i * 0.5}s`,
                } as React.CSSProperties}
              ></div>
            ))}
          </div>
        );

      case 'waves':
        return (
          <div className="global-bg global-bg-waves">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="simple-wave"
                style={{
                  '--delay': `${i * 2}s`,
                  '--opacity': 0.03 + (i * 0.01),
                } as React.CSSProperties}
              ></div>
            ))}
          </div>
        );

      case 'geometric':
        return (
          <div className="global-bg global-bg-geometric">
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="geo-outline"
                style={{
                  '--x': `${(i % 4) * 33}%`,
                  '--y': `${Math.floor(i / 4) * 50}%`,
                  '--rotation': `${i * 45}deg`,
                  '--delay': `${i * 0.8}s`,
                } as React.CSSProperties}
              ></div>
            ))}
          </div>
        );

      case 'noise':
        return (
          <div className="global-bg global-bg-noise">
            <div className="noise-layer"></div>
          </div>
        );

      case 'orbs':
        return (
          <div className="global-bg global-bg-orbs">
            <div className="orb orb-1"></div>
            <div className="orb orb-2"></div>
            <div className="orb orb-3"></div>
          </div>
        );

      case 'circuit':
        return (
          <div className="global-bg global-bg-circuit">
            {[...Array(12)].map((_, i) => (
              <div
                key={i}
                className="circuit-line"
                style={{
                  '--x': `${(i % 4) * 33}%`,
                  '--y': `${Math.floor(i / 4) * 33}%`,
                  '--rotation': `${(i % 2) * 90}deg`,
                  '--delay': `${i * 0.3}s`,
                } as React.CSSProperties}
              ></div>
            ))}
          </div>
        );

      case 'dotmatrix':
        return (
          <div className="global-bg global-bg-dotmatrix">
            {[...Array(200)].map((_, i) => (
              <div
                key={i}
                className="dot-matrix"
                style={{
                  '--x': `${(i % 20) * 5}%`,
                  '--y': `${Math.floor(i / 20) * 5}%`,
                  '--delay': `${(i % 10) * 0.2}s`,
                } as React.CSSProperties}
              ></div>
            ))}
          </div>
        );

      default:
        return null;
    }
  } else {
    // Default cybergrid for non-preview themes
    return (
      <div className="global-bg global-bg-cybergrid">
        <div className="grid-plane">
          {[...Array(20)].map((_, i) => (
            <div key={`h-${i}`} className="grid-line-h" style={{ '--y': `${i * 5}%` } as React.CSSProperties}></div>
          ))}
          {[...Array(20)].map((_, i) => (
            <div key={`v-${i}`} className="grid-line-v" style={{ '--x': `${i * 5}%` } as React.CSSProperties}></div>
          ))}
        </div>
        <div className="grid-glow"></div>
      </div>
    );
  }
};

function App() {
  const [currentPage, setCurrentPage] = useState<PageType>('home');
  const [theme, setTheme] = useState<ThemeType>('bg-preview');
  const [bgType, setBgType] = useState<BgType>('cybergrid');
  const [selectedSkill, setSelectedSkill] = useState<SkillCard | null>(null);
  const [selectedKnowledgeBase, setSelectedKnowledgeBase] = useState<KnowledgeBase | null>(null);

  // Determine if we should show the BG Preview background
  const isBgPreviewTheme = theme === 'bg-preview';

  return (
    <div className="app-container">
      {/* Global Background Switcher - Shows on all pages */}
      <div className="global-bg-switcher">
        <div className="bg-switcher-label">BACKGROUND</div>
        <div className="bg-switcher-options">
          <button
            className={`bg-option-mini ${theme === 'bg-preview' ? 'active' : ''}`}
            onClick={() => setTheme('bg-preview')}
            title="BG Preview (12 styles)"
          >
            <span className="bg-dot bg-dot-gradient"></span>
          </button>
          <button
            className={`bg-option-mini ${theme === 'neon-grid' ? 'active' : ''}`}
            onClick={() => setTheme('neon-grid')}
            title="Neon Grid (Cyber Grid)"
          >
            <span className="bg-dot" style={{ background: '#8b5cf6' }}></span>
          </button>
          <button
            className={`bg-option-mini ${theme === 'neon-void' ? 'active' : ''}`}
            onClick={() => setTheme('neon-void')}
            title="Neon Void"
          >
            <span className="bg-dot" style={{ background: '#00f0ff' }}></span>
          </button>
          <button
            className={`bg-option-mini ${theme === 'abyss-grid' ? 'active' : ''}`}
            onClick={() => setTheme('abyss-grid')}
            title="Abyss Grid"
          >
            <span className="bg-dot" style={{ background: '#10b981' }}></span>
          </button>

        </div>
      </div>

      {/* BG Preview additional background switcher (only shows when BG Preview is active) */}
      {isBgPreviewTheme && (
        <div className="bg-preview-sub-switcher">
          {['cybergrid', 'starfield', 'gradientmesh', 'particles', 'hexagons', 'waves', 'geometric', 'noise', 'orbs', 'circuit', 'dotmatrix'].map((bg) => (
            <button
              key={bg}
              className={`bg-option-mini ${bgType === bg ? 'active' : ''}`}
              onClick={() => setBgType(bg as BgType)}
              title={bg}
            >
              <span className="bg-dot bg-dot-gradient"></span>
            </button>
          ))}
        </div>
      )}

      {/* HOME PAGE */}
      {currentPage === 'home' && theme === 'neon-grid' && (
        <HomePage onSelectPage={setCurrentPage} />
      )}

      {currentPage === 'home' && theme === 'neon-void' && (
        <HomePageDemo onSelectPage={setCurrentPage} />
      )}

      {currentPage === 'home' && theme === 'abyss-grid' && (
        <HomePageDemo2 onSelectPage={setCurrentPage} />
      )}

      {currentPage === 'home' && theme === 'bg-preview' && (
        <HomePageDemo3 onSelectPage={setCurrentPage} />
      )}

      {/* SKILL LIST PAGE */}
      {currentPage === 'skill' && (
        <div className="neon-skill-page">
          {/*<GlobalBackground theme={theme} bgType={bgType} />*/}

          <header className="skill-page-header">
            <button className="neon-back-button" onClick={() => setCurrentPage('home')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 12H5M12 19l-7-7 7-7"></path>
              </svg>
              返回首页
            </button>
            <h1 className="skill-page-title">Skill 技能</h1>
          </header>

          <SkillListPage
            onBackToHome={() => setCurrentPage('home')}
            onSelectSkill={(skill) => {
              setSelectedSkill(skill);
              setCurrentPage('skill-files');
            }}
          />
        </div>
      )}

      {/* SKILL FILE LIST PAGE */}
      {currentPage === 'skill-files' && selectedSkill && (
        <div className="neon-skill-file-page">
          <GlobalBackground theme={theme} bgType={bgType} />

          <SkillFileListPage
            skill={selectedSkill}
            onBackToSkills={() => setCurrentPage('skill')}
          />
        </div>
      )}

      {/* KNOWLEDGE BASE LIST PAGE */}
      {currentPage === 'knowledge-base' && (
        <div className="neon-knowledge-base-page">
          <header className="knowledge-base-page-header">
            <button className="neon-back-button" onClick={() => setCurrentPage('home')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 12H5M12 19l-7-7 7-7"></path>
              </svg>
              返回首页
            </button>
            <h1 className="knowledge-base-page-title">知识库管理</h1>
          </header>

          <KnowledgeBaseListPage
            onBackToHome={() => setCurrentPage('home')}
            onSelectKnowledgeBase={(kb) => {
              setSelectedKnowledgeBase(kb);
              setCurrentPage('knowledge-base-detail');
            }}
          />
        </div>
      )}

      {/* KNOWLEDGE BASE DETAIL PAGE */}
      {currentPage === 'knowledge-base-detail' && selectedKnowledgeBase && (
        <div className="neon-knowledge-base-detail-page">
          <header className="knowledge-base-detail-page-header">
            <button className="neon-back-button" onClick={() => setCurrentPage('knowledge-base')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 12H5M12 19l-7-7 7-7"></path>
              </svg>
              返回列表
            </button>
            <h1 className="knowledge-base-detail-page-title">{selectedKnowledgeBase.name}</h1>
          </header>

          <KnowledgeBaseDetailPage
            kb={selectedKnowledgeBase}
            onBackToHome={() => setCurrentPage('home')}
          />
        </div>
      )}
    </div>
  );
}

export default App;
