import { mkdir, rename, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

// Each invocation owns a fresh directory. A killed process leaves status=running,
// never a previous run's success. Rename prevents readers seeing truncated JSON.
export async function recordProbe(directory, metadata, probe) {
  await mkdir(directory, { recursive: true })
  const path = join(directory, 'report.json')
  const report = { schemaVersion: 1, ...metadata, status: 'running',
    startedAt: new Date().toISOString(), endedAt: null, profiles: [], errors: [] }
  const checkpoint = async () => {
    await writeFile(path + '.tmp', JSON.stringify(report, null, 2) + '\n')
    await rename(path + '.tmp', path)
  }
  await checkpoint()
  try {
    await probe(report, checkpoint)
    if (report.errors.length) throw new Error('Graphics probe reported runtime errors')
    report.status = 'passed'
  } catch (error) {
    report.status = 'failed'
    report.failure = error.message
    throw error
  } finally {
    report.endedAt = new Date().toISOString()
    await checkpoint()
  }
  return report
}
