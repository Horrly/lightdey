const BAND_ROWS = [
  ["A", "20 hours"],
  ["B", "16 hours"],
  ["C", "12 hours"],
  ["D", "8 hours"],
  ["E", "4 hours"],
];

export default function About() {
  return (
    <article className="space-y-6 text-slate-300">
      <h1 className="text-2xl font-bold text-white">How LightDey works</h1>

      <section className="card space-y-2 p-5 text-sm leading-relaxed">
        <h2 className="font-semibold text-white">Reports from neighbours</h2>
        <p>
          Anyone can tap <strong className="text-glow-300">Light dey</strong> or <strong className="text-indigo-300">No light</strong> for their
          area. There's no sign-up. We combine recent reports into a live status. When people disagree, the majority in each 10-minute window
          wins.
        </p>
        <p>
          A status lasts until someone reports a change. If nobody reports for 4 hours, we show <em>No recent reports</em> instead of guessing.
        </p>
      </section>

      <section className="card space-y-2 p-5 text-sm leading-relaxed">
        <h2 className="font-semibold text-white">Tariff bands</h2>
        <p>Under NERC's Service-Based Tariff, each band promises a minimum daily supply:</p>
        <table className="w-full text-left">
          <tbody className="divide-y divide-night-700">
            {BAND_ROWS.map(([band, hours]) => (
              <tr key={band}>
                <td className="py-1.5 font-medium text-white">Band {band}</td>
                <td className="py-1.5">at least {hours} a day</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p>
          Pick your band on an area's page (it's printed on your bill), and LightDey compares it with the hours your neighbours reported.
          Crowd reports are estimates, not meter readings. They're still a useful record when you talk to your DisCo.
        </p>
      </section>

      <section className="card space-y-2 p-5 text-sm leading-relaxed">
        <h2 className="font-semibold text-white">Privacy</h2>
        <p>
          We don't ask for your name, phone number or location. Your browser gets a random ID so you can correct your own report, and we
          store only a scrambled version of it and of your IP address to stop spam.
        </p>
      </section>

      <section className="card space-y-2 p-5 text-sm leading-relaxed">
        <h2 className="font-semibold text-white">Alerts</h2>
        <p>
          Turn on alerts for an area and you'll get a notification when people there report that light is back. On iPhone, first add LightDey
          to your home screen (Share → Add to Home Screen).
        </p>
      </section>
    </article>
  );
}
