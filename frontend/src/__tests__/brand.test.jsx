import { APP_NAME } from '../brand';
import brand from '../../brand/brand.json';

test('APP_NAME comes from brand/brand.json', () => {
  expect(APP_NAME).toBe(brand.name);
  expect(APP_NAME).toBeTruthy();
});
