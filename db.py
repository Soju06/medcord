from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import env

Base = declarative_base()

engine = create_async_engine(
    env.DATABASE_URL,
    pool_pre_ping=True,
    echo=env.DEBUG,
    **(
        {}
        if make_url(env.DATABASE_URL).get_dialect().name == "sqlite"
        else {
            "pool_size": 1,
            "max_overflow": 10,
        }
    ),
)

session = sessionmaker[AsyncSession](bind=engine, class_=AsyncSession)


def scope() -> AsyncSession:
    return session()


async def create_all():
    url = make_url(env.DATABASE_URL)
    dialect = url.get_dialect().name
    database = url.database
    new_engine = create_async_engine(
        url.set(database="").render_as_string(False),
        echo=env.DEBUG,
    )

    async with new_engine.begin() as conn:
        if dialect != "sqlite":
            await conn.execute(
                text(
                    "SELECT 'CREATE DATABASE {0}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{0}')\gexec".format(
                        database
                    )
                    if dialect == "postgresql"
                    else f"CREATE DATABASE IF NOT EXISTS {database}"
                )
            )

    new_engine.dispose()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
