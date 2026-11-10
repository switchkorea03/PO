import base from './playwright.config.mjs';
import {resolve} from 'node:path';
export default {...base,testMatch:'*.spec.mjs',outputDir:resolve('../../.runtime/2026-10-27-e2e-results'),
 reporter:[['list'],['json',{outputFile:resolve('../../.runtime/2026-10-27-e2e-report.json')}]],
 webServer:{...base.webServer,reuseExistingServer:true}};
