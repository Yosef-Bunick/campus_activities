// The app's name, from brand/brand.json (the one place to rename the app;
// see brand/README.md). A plain JSON import works the same in dev, build and Vitest.
import { name } from '../brand/brand.json';

export const APP_NAME = name;
