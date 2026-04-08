export const siteConfig = {
    name: 'Max Wels',
    tagline: 'Data. Systems. Travel. Strength.',
    description:
        'I build structure, explore freedom, and work on projects that connect technology with real life.',
    url: 'https://maxwels.com',
    ogImage: '/images/og-image.jpg',
} as const;

export const navLinks = [
    { label: 'Home', href: '/' },
    { label: 'Projects', href: '/projects' },
    { label: 'About', href: '/about' },
    { label: 'Life', href: '/life' },
    { label: 'Connect', href: '/connect' },
] as const;

export const socialLinks = [
    {
        label: 'LinkedIn',
        href: 'https://linkedin.com/in/your-profile',
        icon: 'linkedin',
    },
    {
        label: 'GitHub',
        href: 'https://github.com/your-username',
        icon: 'github',
    },
    {
        label: 'Instagram',
        href: 'https://instagram.com/your-handle',
        icon: 'instagram',
    },
    {
        label: 'Email',
        href: 'mailto:hello@maxwels.com',
        icon: 'email',
    },
] as const;

export const skills = [
    {
        title: 'Data & Analysis',
        description:
            'I work with data to uncover patterns, answer real questions and turn complexity into decisions.',
        icon: '◆',
    },
    {
        title: 'Automation & AI Workflows',
        description:
            "I'm interested in building lean systems that reduce friction — from process automation to LLM-supported workflows.",
        icon: '⬡',
    },
    {
        title: 'Projects & Structure',
        description:
            'I bring together ideas, tools and people to create momentum, clarity and usable results.',
        icon: '△',
    },
] as const;

export const skillTags = [
    'Python',
    'SQL',
    'Data Analysis',
    'NLP',
    'Automation',
    'Dashboards',
    'AI Workflows',
    'Process Thinking',
    'Project Coordination',
] as const;

export const lifeCards = [
    {
        title: 'Calisthenics',
        description: 'Strength, control, discipline.',
        icon: '⬥',
    },
    {
        title: 'Travel',
        description: 'Movement, freedom, perspective.',
        icon: '◈',
    },
    {
        title: 'Music & Culture',
        description: 'Intensity, atmosphere, connection.',
        icon: '◎',
    },
    {
        title: 'Systems & Ideas',
        description: 'Turning chaos into structure.',
        icon: '⬢',
    },
] as const;

export const currentFocus = [
    'Building skills in data, automation and AI',
    'Training calisthenics and staying lean',
    'Planning future travel and location-independent work',
    'Exploring projects that combine structure, freedom and creativity',
] as const;
