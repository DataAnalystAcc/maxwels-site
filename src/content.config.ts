import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const projects = defineCollection({
    loader: glob({ pattern: '**/*.md', base: './src/content/projects' }),
    schema: z.object({
        title: z.string(),
        description: z.string(),
        longDescription: z.string().optional(),
        tags: z.array(z.string()),
        image: z.string().optional(),
        link: z.string().optional(),
        featured: z.boolean().default(false),
        order: z.number().default(0),
    }),
});

const journal = defineCollection({
    loader: glob({ pattern: '**/*.md', base: './src/content/journal' }),
    schema: z.object({
        title: z.string(),
        description: z.string(),
        date: z.date(),
        tags: z.array(z.string()).default([]),
        draft: z.boolean().default(true),
    }),
});

export const collections = { projects, journal };
