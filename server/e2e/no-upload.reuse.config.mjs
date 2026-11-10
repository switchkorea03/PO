// Attach only to the dedicated server/e2e/serve.py test server on port 8001.
// Useful on Windows when managed-server shutdown retains inherited handles.
import base from './playwright.config.mjs';
import {resolve} from 'node:path';
export default {
 ...base,
 testMatch:'no-upload.spec.mjs',
 outputDir:'no-upload-test-results',
 reporter:[['list'],['json',{outputFile:resolve('../../.runtime/no-upload-report.json')}]],
 webServer:{...base.webServer,reuseExistingServer:true}
};
