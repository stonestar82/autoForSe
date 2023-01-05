import asyncio
from src.Processing import Processing

class App:
	async def exec(self):
		self.window = Processing(asyncio.get_event_loop())
		await self.window.show();

asyncio.run(App().exec(), debug=True)