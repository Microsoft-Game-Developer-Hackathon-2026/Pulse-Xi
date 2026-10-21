import { readFile } from 'node:fs/promises'
import validator from 'gltf-validator'

const root = new URL('../../', import.meta.url)
const manifest = JSON.parse(await readFile(new URL('assets/manifest.json', root), 'utf8'))
let errors = 0
for (const asset of manifest.assets) {
  const report = await validator.validateBytes(new Uint8Array(await readFile(new URL(asset.output, root))), {
    uri: asset.output, maxIssues: 100,
    externalResourceFunction: async () => { throw new Error('External resources prohibited in this original kit') },
  })
  console.log(JSON.stringify({ asset: asset.name, errors: report.issues.numErrors, warnings: report.issues.numWarnings, messages: report.issues.messages }))
  errors += report.issues.numErrors
}
if (errors) process.exitCode = 1
