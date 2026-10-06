import Panel from './Panel';
import { useDashboard } from '../app/DashboardContext';
import { JsonData, ResourceState } from './ApiState';
export default function HistoryLog({ full = false }: { full?: boolean }) {
  const { sensors, detections } = useDashboard();
  function exportJson() {
    const url = URL.createObjectURL(new Blob([JSON.stringify({ sensors: sensors.data, detections: detections.data }, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'leafnode-history.json'; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <Panel title="History / Log" className={'history-panel ' + (full ? 'history-full' : '')}
    action={<button className="export-button" disabled={!sensors.data && !detections.data} onClick={exportJson}>Export JSON</button>}>
    {[{ name: 'Sensor history', resource: sensors }, { name: 'Detection history', resource: detections }].map(({ name, resource }) => <section className="api-history" key={name}>
      <h3>{name}</h3><ResourceState resource={resource} empty={!resource.data?.data.length} message={'No ' + name.toLowerCase() + ' available.'}/>
      {resource.data && <><p className="api-state">{resource.data.count} records reported{!full && resource.data.data.length > 5 ? ' · showing first 5 returned' : ''}</p>
        {(full ? resource.data.data : resource.data.data.slice(0, 5)).map((row, index) => <details key={index}><summary>Record {index + 1}</summary><JsonData value={row}/></details>)}</>}
    </section>)}
  </Panel>;
}
