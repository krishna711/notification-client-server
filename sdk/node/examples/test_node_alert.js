const { Notifier } = require('../index');

async function main() {
  console.log('='.repeat(60));
  console.log('Sending Test Alert from Node.js SDK to Notification Gateway');
  console.log('='.repeat(60));

  const notify = new Notifier({
    endpoint: process.env.NOTIFIER_SERVER_URL || 'https://notify.yotek.net',
    apiKey: process.env.NOTIFIER_API_KEY || 'hFvIbyyAEc8aZDJOB3858KZS1XkZKK38',
    defaultSource: 'node-order-service'
  });

  try {
    console.log('\nDispatching Trade Alert from Node.js...');
    const result = await notify.tradeAlert(
      'Node.js: Order Executed',
      'NSE: INFY 1950 CE filled 200 qty @ 24.50. Target: 32.00',
      'high',
      { symbol: 'INFY1950CE', qty: 200, price: 24.5, platform: 'Node.js' }
    );
    console.log('✓ Success! Gateway Response:', result);

    console.log('\nDispatching Server Health Alert from Node.js...');
    const srvResult = await notify.serverAlert(
      'Node.js: Memory Alert',
      'Heap usage exceeded 85% threshold (1.4 GB / 1.6 GB)',
      'critical',
      { heapUsedMB: 1420, pid: 4892 }
    );
    console.log('✓ Success! Gateway Response:', srvResult);

    console.log('\nAll Node.js alerts delivered successfully!');
  } catch (err) {
    console.error('Failed to send notification:', err.message);
  }
}

main();
