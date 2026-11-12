apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   [SQL: INSERT INTO invites (id, code_hash, created_by, used_by, expires_at, used_at, note) VALUES ($1::UUID, $2::VARCHAR, $3::UUID, $4::UUID, $5::TIMESTAMP WITH TIME ZONE, $6::TIMESTAMP WITH TIME ZONE, $7::VARCHAR) RETURNING invites.created_at]
E   [parameters: (UUID('481e9fc6-8189-4db6-a7e1-368b5f8e8695'), '75de860f6d85b9924825da6d7ef741300115a0751657bf92627c6f076c75c8f9', UUID('d8654a11-703e-403c-a037-c181a5c26e2e'), None, datetime.datetime(2026, 11, 15, 14, 12, 39, 656490), None, None)]
E   (Background on this error at: https://sqlalche.me/e/21/gkpj)
_______________________________________________________________________________________________ test_wrong_expected_version_conflicts ________________________________________________________________________________________________ 
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:605: in _prepare_and_execute
    self._rows = deque(await prepared_stmt.fetch(*parameters))
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:177: in fetch
    data = await self.__bind_execute(args, 0, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:268: in __bind_execute
    data, status, _ = await self.__do_execute(
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:257: in __do_execute
    return await executor(protocol)
           ^^^^^^^^^^^^^^^^^^^^^^^^
asyncpg/protocol/protocol.pyx:197: in bind_execute
    ???
E   asyncpg.exceptions.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   DETAIL:  Key (created_by)=(2abdae73-40b2-41cc-bc2d-c66bd0b650eb) is not present in table "users".

The above exception was the direct cause of the following exception:
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"

The above exception was the direct cause of the following exception:
apps\api\tests\integration\test_record_version_conflict.py:39: in test_wrong_expected_version_conflicts
    user_id, _, _ = await register_user(http, f"vc-{uuid.uuid4().hex[:8]}")
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:118: in register_user
    invite_code = await create_invite()
                  ^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:111: in create_invite
    await _current_session.commit()
apps\api\.venv\Lib\site-packages\sqlalchemy\ext\asyncio\session.py:1309: in commit
    await greenlet_spawn(self.sync_session.commit)
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:212: in greenlet_spawn
    result = context.switch(value)
             ^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:2177: in commit
    trans.commit(_to_root=True)
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction.commit>:2: in commit
    return target(fn, self, _to_root=_to_root)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1412: in commit
    self._prepare_impl()
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction._prepare_impl>:2: in _prepare_impl
    return target(fn, self)
           ^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1386: in _prepare_impl
    self.session.flush()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4626: in flush
    self._flush(objects)
<sqlalchemy generated warned() wrapper for sqlalchemy.orm.session.Session._flush>:2: in _flush
    return target(fn, self, objects=objects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\deprecations.py:281: in warned
    return fn(*args, **kwargs)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4769: in _flush
    with util.safe_reraise():
         ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\langhelpers.py:166: in __exit__
    raise exc_value.with_traceback(exc_tb)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4730: in _flush
    flush_context.execute()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:467: in execute
    rec.execute(self)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:643: in execute
    util.preloaded.orm_persistence._save_obj(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:92: in _save_obj
    _emit_insert_statements(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:1250: in _emit_insert_statements
    result = connection.execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1494: in execute
    return meth(
apps\api\.venv\Lib\site-packages\sqlalchemy\sql\elements.py:534: in _execute_on_connection
    return connection._execute_clauseelement(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1714: in _execute_clauseelement
    ret = self._execute_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1868: in _execute_context
    return self._exec_single_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1996: in _exec_single_context
    self._handle_dbapi_exception(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:2351: in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   [SQL: INSERT INTO invites (id, code_hash, created_by, used_by, expires_at, used_at, note) VALUES ($1::UUID, $2::VARCHAR, $3::UUID, $4::UUID, $5::TIMESTAMP WITH TIME ZONE, $6::TIMESTAMP WITH TIME ZONE, $7::VARCHAR) RETURNING invites.created_at]
E   [parameters: (UUID('e92d0989-c06a-46fe-86c5-8ddba479b5a8'), '3b84227d59b5fa026d5d59793b895b48e2cd37a85eaa1e4b51f5d1b367d2354e', UUID('2abdae73-40b2-41cc-bc2d-c66bd0b650eb'), None, datetime.datetime(2026, 11, 15, 14, 12, 40, 435761), None, None)]
E   (Background on this error at: https://sqlalche.me/e/21/gkpj)
_________________________________________________________________________________________ test_correct_version_updates_and_records_revision __________________________________________________________________________________________ 
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:605: in _prepare_and_execute
    self._rows = deque(await prepared_stmt.fetch(*parameters))
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:177: in fetch
    data = await self.__bind_execute(args, 0, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:268: in __bind_execute
    data, status, _ = await self.__do_execute(
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:257: in __do_execute
    return await executor(protocol)
           ^^^^^^^^^^^^^^^^^^^^^^^^
asyncpg/protocol/protocol.pyx:197: in bind_execute
    ???
E   asyncpg.exceptions.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   DETAIL:  Key (created_by)=(e4ada309-6ef7-4307-bcc2-2b19a4719dd2) is not present in table "users".

The above exception was the direct cause of the following exception:
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"

The above exception was the direct cause of the following exception:
apps\api\tests\integration\test_record_version_conflict.py:51: in test_correct_version_updates_and_records_revision
    user_id, _, _ = await register_user(http, f"vc2-{uuid.uuid4().hex[:8]}")
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:118: in register_user
    invite_code = await create_invite()
                  ^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:111: in create_invite
    await _current_session.commit()
apps\api\.venv\Lib\site-packages\sqlalchemy\ext\asyncio\session.py:1309: in commit
    await greenlet_spawn(self.sync_session.commit)
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:212: in greenlet_spawn
    result = context.switch(value)
             ^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:2177: in commit
    trans.commit(_to_root=True)
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction.commit>:2: in commit
    return target(fn, self, _to_root=_to_root)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1412: in commit
    self._prepare_impl()
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction._prepare_impl>:2: in _prepare_impl
    return target(fn, self)
           ^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1386: in _prepare_impl
    self.session.flush()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4626: in flush
    self._flush(objects)
<sqlalchemy generated warned() wrapper for sqlalchemy.orm.session.Session._flush>:2: in _flush
    return target(fn, self, objects=objects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\deprecations.py:281: in warned
    return fn(*args, **kwargs)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4769: in _flush
    with util.safe_reraise():
         ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\langhelpers.py:166: in __exit__
    raise exc_value.with_traceback(exc_tb)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4730: in _flush
    flush_context.execute()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:467: in execute
    rec.execute(self)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:643: in execute
    util.preloaded.orm_persistence._save_obj(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:92: in _save_obj
    _emit_insert_statements(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:1250: in _emit_insert_statements
    result = connection.execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1494: in execute
    return meth(
apps\api\.venv\Lib\site-packages\sqlalchemy\sql\elements.py:534: in _execute_on_connection
    return connection._execute_clauseelement(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1714: in _execute_clauseelement
    ret = self._execute_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1868: in _execute_context
    return self._exec_single_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1996: in _exec_single_context
    self._handle_dbapi_exception(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:2351: in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   [SQL: INSERT INTO invites (id, code_hash, created_by, used_by, expires_at, used_at, note) VALUES ($1::UUID, $2::VARCHAR, $3::UUID, $4::UUID, $5::TIMESTAMP WITH TIME ZONE, $6::TIMESTAMP WITH TIME ZONE, $7::VARCHAR) RETURNING invites.created_at]
E   [parameters: (UUID('3cf7c667-2e0f-4def-a12d-36ca7a254fab'), 'dfce45542af3813ead98fafd3ef0a717c51fe7da95b768c15376906395763c0b', UUID('e4ada309-6ef7-4307-bcc2-2b19a4719dd2'), None, datetime.datetime(2026, 11, 15, 14, 12, 41, 243450), None, None)]
E   (Background on this error at: https://sqlalche.me/e/21/gkpj)
___________________________________________________________________________________________ test_replay_same_event_returns_already_applied ___________________________________________________________________________________________ 
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:605: in _prepare_and_execute
    self._rows = deque(await prepared_stmt.fetch(*parameters))
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:177: in fetch
    data = await self.__bind_execute(args, 0, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:268: in __bind_execute
    data, status, _ = await self.__do_execute(
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:257: in __do_execute
    return await executor(protocol)
           ^^^^^^^^^^^^^^^^^^^^^^^^
asyncpg/protocol/protocol.pyx:197: in bind_execute
    ???
E   asyncpg.exceptions.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   DETAIL:  Key (created_by)=(7a674569-917b-4d34-9765-7d87101f494c) is not present in table "users".

The above exception was the direct cause of the following exception:
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"

The above exception was the direct cause of the following exception:
apps\api\tests\integration\test_sync_idempotency.py:34: in test_replay_same_event_returns_already_applied
    user_id, csrf, _ = await register_user(http, f"sync-{uuid.uuid4().hex[:8]}")
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:118: in register_user
    invite_code = await create_invite()
                  ^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:111: in create_invite
    await _current_session.commit()
apps\api\.venv\Lib\site-packages\sqlalchemy\ext\asyncio\session.py:1309: in commit
    await greenlet_spawn(self.sync_session.commit)
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:212: in greenlet_spawn
    result = context.switch(value)
             ^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:2177: in commit
    trans.commit(_to_root=True)
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction.commit>:2: in commit
    return target(fn, self, _to_root=_to_root)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1412: in commit
    self._prepare_impl()
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction._prepare_impl>:2: in _prepare_impl
    return target(fn, self)
           ^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1386: in _prepare_impl
    self.session.flush()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4626: in flush
    self._flush(objects)
<sqlalchemy generated warned() wrapper for sqlalchemy.orm.session.Session._flush>:2: in _flush
    return target(fn, self, objects=objects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\deprecations.py:281: in warned
    return fn(*args, **kwargs)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4769: in _flush
    with util.safe_reraise():
         ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\langhelpers.py:166: in __exit__
    raise exc_value.with_traceback(exc_tb)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4730: in _flush
    flush_context.execute()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:467: in execute
    rec.execute(self)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:643: in execute
    util.preloaded.orm_persistence._save_obj(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:92: in _save_obj
    _emit_insert_statements(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:1250: in _emit_insert_statements
    result = connection.execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1494: in execute
    return meth(
apps\api\.venv\Lib\site-packages\sqlalchemy\sql\elements.py:534: in _execute_on_connection
    return connection._execute_clauseelement(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1714: in _execute_clauseelement
    ret = self._execute_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1868: in _execute_context
    return self._exec_single_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1996: in _exec_single_context
    self._handle_dbapi_exception(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:2351: in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   [SQL: INSERT INTO invites (id, code_hash, created_by, used_by, expires_at, used_at, note) VALUES ($1::UUID, $2::VARCHAR, $3::UUID, $4::UUID, $5::TIMESTAMP WITH TIME ZONE, $6::TIMESTAMP WITH TIME ZONE, $7::VARCHAR) RETURNING invites.created_at]
E   [parameters: (UUID('7eac4a0c-2752-4ac0-894f-fc4579fc3d8b'), '19648174fc8bea7c3127bd3a8424378dad32e1968cdee095facaf5cc5d23fa67', UUID('7a674569-917b-4d34-9765-7d87101f494c'), None, datetime.datetime(2026, 11, 15, 14, 12, 42, 15474), None, None)]
E   (Background on this error at: https://sqlalche.me/e/21/gkpj)
______________________________________________________________________________________________ test_same_id_different_content_conflicts ______________________________________________________________________________________________ 
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:605: in _prepare_and_execute
    self._rows = deque(await prepared_stmt.fetch(*parameters))
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:177: in fetch
    data = await self.__bind_execute(args, 0, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:268: in __bind_execute
    data, status, _ = await self.__do_execute(
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:257: in __do_execute
    return await executor(protocol)
           ^^^^^^^^^^^^^^^^^^^^^^^^
asyncpg/protocol/protocol.pyx:197: in bind_execute
    ???
E   asyncpg.exceptions.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   DETAIL:  Key (created_by)=(56c4b16e-d871-436c-ae8e-ce131b406a61) is not present in table "users".

The above exception was the direct cause of the following exception:
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"

The above exception was the direct cause of the following exception:
apps\api\tests\integration\test_sync_idempotency.py:62: in test_same_id_different_content_conflicts
    _, csrf, _ = await register_user(http, f"conflict-{uuid.uuid4().hex[:8]}")
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:118: in register_user
    invite_code = await create_invite()
                  ^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:111: in create_invite
    await _current_session.commit()
apps\api\.venv\Lib\site-packages\sqlalchemy\ext\asyncio\session.py:1309: in commit
    await greenlet_spawn(self.sync_session.commit)
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:212: in greenlet_spawn
    result = context.switch(value)
             ^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:2177: in commit
    trans.commit(_to_root=True)
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction.commit>:2: in commit
    return target(fn, self, _to_root=_to_root)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1412: in commit
    self._prepare_impl()
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction._prepare_impl>:2: in _prepare_impl
    return target(fn, self)
           ^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1386: in _prepare_impl
    self.session.flush()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4626: in flush
    self._flush(objects)
<sqlalchemy generated warned() wrapper for sqlalchemy.orm.session.Session._flush>:2: in _flush
    return target(fn, self, objects=objects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\deprecations.py:281: in warned
    return fn(*args, **kwargs)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4769: in _flush
    with util.safe_reraise():
         ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\langhelpers.py:166: in __exit__
    raise exc_value.with_traceback(exc_tb)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4730: in _flush
    flush_context.execute()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:467: in execute
    rec.execute(self)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:643: in execute
    util.preloaded.orm_persistence._save_obj(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:92: in _save_obj
    _emit_insert_statements(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:1250: in _emit_insert_statements
    result = connection.execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1494: in execute
    return meth(
apps\api\.venv\Lib\site-packages\sqlalchemy\sql\elements.py:534: in _execute_on_connection
    return connection._execute_clauseelement(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1714: in _execute_clauseelement
    ret = self._execute_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1868: in _execute_context
    return self._exec_single_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1996: in _exec_single_context
    self._handle_dbapi_exception(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:2351: in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   [SQL: INSERT INTO invites (id, code_hash, created_by, used_by, expires_at, used_at, note) VALUES ($1::UUID, $2::VARCHAR, $3::UUID, $4::UUID, $5::TIMESTAMP WITH TIME ZONE, $6::TIMESTAMP WITH TIME ZONE, $7::VARCHAR) RETURNING invites.created_at]
E   [parameters: (UUID('54547a6e-cb5a-4dcf-945f-0cae97136ad1'), 'b0e771d86d3cdbcaa47a2385081f8f4340f0ee9a47a8dc7dcdd0c30464b5e0bb', UUID('56c4b16e-d871-436c-ae8e-ce131b406a61'), None, datetime.datetime(2026, 11, 15, 14, 12, 42, 781549), None, None)]
E   (Background on this error at: https://sqlalche.me/e/21/gkpj)
___________________________________________________________________________________________ test_set_without_parent_is_dependency_pending ____________________________________________________________________________________________ 
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:605: in _prepare_and_execute
    self._rows = deque(await prepared_stmt.fetch(*parameters))
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:177: in fetch
    data = await self.__bind_execute(args, 0, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:268: in __bind_execute
    data, status, _ = await self.__do_execute(
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:257: in __do_execute
    return await executor(protocol)
           ^^^^^^^^^^^^^^^^^^^^^^^^
asyncpg/protocol/protocol.pyx:197: in bind_execute
    ???
E   asyncpg.exceptions.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   DETAIL:  Key (created_by)=(a0cfb3c7-cf81-47f2-bbda-fb3940eff62d) is not present in table "users".

The above exception was the direct cause of the following exception:
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"

The above exception was the direct cause of the following exception:
apps\api\tests\integration\test_sync_idempotency.py:82: in test_set_without_parent_is_dependency_pending
    _, csrf, _ = await register_user(http, f"dep-{uuid.uuid4().hex[:8]}")
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:118: in register_user
    invite_code = await create_invite()
                  ^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:111: in create_invite
    await _current_session.commit()
apps\api\.venv\Lib\site-packages\sqlalchemy\ext\asyncio\session.py:1309: in commit
    await greenlet_spawn(self.sync_session.commit)
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:212: in greenlet_spawn
    result = context.switch(value)
             ^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:2177: in commit
    trans.commit(_to_root=True)
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction.commit>:2: in commit
    return target(fn, self, _to_root=_to_root)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1412: in commit
    self._prepare_impl()
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction._prepare_impl>:2: in _prepare_impl
    return target(fn, self)
           ^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1386: in _prepare_impl
    self.session.flush()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4626: in flush
    self._flush(objects)
<sqlalchemy generated warned() wrapper for sqlalchemy.orm.session.Session._flush>:2: in _flush
    return target(fn, self, objects=objects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\deprecations.py:281: in warned
    return fn(*args, **kwargs)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4769: in _flush
    with util.safe_reraise():
         ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\langhelpers.py:166: in __exit__
    raise exc_value.with_traceback(exc_tb)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4730: in _flush
    flush_context.execute()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:467: in execute
    rec.execute(self)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:643: in execute
    util.preloaded.orm_persistence._save_obj(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:92: in _save_obj
    _emit_insert_statements(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:1250: in _emit_insert_statements
    result = connection.execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1494: in execute
    return meth(
apps\api\.venv\Lib\site-packages\sqlalchemy\sql\elements.py:534: in _execute_on_connection
    return connection._execute_clauseelement(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1714: in _execute_clauseelement
    ret = self._execute_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1868: in _execute_context
    return self._exec_single_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1996: in _exec_single_context
    self._handle_dbapi_exception(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:2351: in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   [SQL: INSERT INTO invites (id, code_hash, created_by, used_by, expires_at, used_at, note) VALUES ($1::UUID, $2::VARCHAR, $3::UUID, $4::UUID, $5::TIMESTAMP WITH TIME ZONE, $6::TIMESTAMP WITH TIME ZONE, $7::VARCHAR) RETURNING invites.created_at]
E   [parameters: (UUID('e7408cae-ed5d-4767-b055-fd82452fbb65'), 'fe0ccd2bfec8d476d80c5ffa65169865f543f97cf02563d3ed3e390b6d1836e1', UUID('a0cfb3c7-cf81-47f2-bbda-fb3940eff62d'), None, datetime.datetime(2026, 11, 15, 14, 12, 43, 567396), None, None)]
E   (Background on this error at: https://sqlalche.me/e/21/gkpj)
___________________________________________________________________________________________ test_failed_middle_event_keeps_first_and_third ___________________________________________________________________________________________ 
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:605: in _prepare_and_execute
    self._rows = deque(await prepared_stmt.fetch(*parameters))
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:177: in fetch
    data = await self.__bind_execute(args, 0, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:268: in __bind_execute
    data, status, _ = await self.__do_execute(
apps\api\.venv\Lib\site-packages\asyncpg\prepared_stmt.py:257: in __do_execute
    return await executor(protocol)
           ^^^^^^^^^^^^^^^^^^^^^^^^
asyncpg/protocol/protocol.pyx:197: in bind_execute
    ???
E   asyncpg.exceptions.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   DETAIL:  Key (created_by)=(7b8690ea-4bcd-453d-a545-ae7d2aa17026) is not present in table "users".

The above exception was the direct cause of the following exception:
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ForeignKeyViolationError: insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"

The above exception was the direct cause of the following exception:
apps\api\tests\integration\test_sync_partial_failure.py:33: in test_failed_middle_event_keeps_first_and_third
    _, csrf, _ = await register_user(http, f"partial-{uuid.uuid4().hex[:8]}")
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:118: in register_user
    invite_code = await create_invite()
                  ^^^^^^^^^^^^^^^^^^^^^
apps\api\tests\integration\conftest.py:111: in create_invite
    await _current_session.commit()
apps\api\.venv\Lib\site-packages\sqlalchemy\ext\asyncio\session.py:1309: in commit
    await greenlet_spawn(self.sync_session.commit)
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:212: in greenlet_spawn
    result = context.switch(value)
             ^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:2177: in commit
    trans.commit(_to_root=True)
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction.commit>:2: in commit
    return target(fn, self, _to_root=_to_root)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1412: in commit
    self._prepare_impl()
<sqlalchemy generated _go() wrapper for sqlalchemy.orm.session.SessionTransaction._prepare_impl>:2: in _prepare_impl
    return target(fn, self)
           ^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py:137: in _go
    ret_value = fn(self, *arg, **kw)
                ^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:1386: in _prepare_impl
    self.session.flush()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4626: in flush
    self._flush(objects)
<sqlalchemy generated warned() wrapper for sqlalchemy.orm.session.Session._flush>:2: in _flush
    return target(fn, self, objects=objects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\deprecations.py:281: in warned
    return fn(*args, **kwargs)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4769: in _flush
    with util.safe_reraise():
         ^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\langhelpers.py:166: in __exit__
    raise exc_value.with_traceback(exc_tb)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\session.py:4730: in _flush
    flush_context.execute()
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:467: in execute
    rec.execute(self)
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py:643: in execute
    util.preloaded.orm_persistence._save_obj(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:92: in _save_obj
    _emit_insert_statements(
apps\api\.venv\Lib\site-packages\sqlalchemy\orm\persistence.py:1250: in _emit_insert_statements
    result = connection.execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1494: in execute
    return meth(
apps\api\.venv\Lib\site-packages\sqlalchemy\sql\elements.py:534: in _execute_on_connection
    return connection._execute_clauseelement(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1714: in _execute_clauseelement
    ret = self._execute_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1868: in _execute_context
    return self._exec_single_context(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1996: in _exec_single_context
    self._handle_dbapi_exception(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:2351: in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\base.py:1977: in _exec_single_context
    self.dialect.do_execute(
apps\api\.venv\Lib\site-packages\sqlalchemy\engine\default.py:1192: in do_execute
    cursor.execute(statement, parameters)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:656: in execute
    await_(self._prepare_and_execute(operation, parameters))
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:167: in await_
    return current.parent.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\util\concurrency.py:205: in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:618: in _prepare_and_execute
    self._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:568: in _handle_exception
    self._adapt_connection._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:847: in _handle_exception
    super()._handle_exception(error)
apps\api\.venv\Lib\site-packages\sqlalchemy\connectors\asyncio.py:412: in _handle_exception
    self._handle_exception_no_connection(self.dbapi, error)
apps\api\.venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py:840: in _handle_exception_no_connection
    raise translated_error from error
E   sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
E   [SQL: INSERT INTO invites (id, code_hash, created_by, used_by, expires_at, used_at, note) VALUES ($1::UUID, $2::VARCHAR, $3::UUID, $4::UUID, $5::TIMESTAMP WITH TIME ZONE, $6::TIMESTAMP WITH TIME ZONE, $7::VARCHAR) RETURNING invites.created_at]
E   [parameters: (UUID('fb633fa3-c6c1-415f-b02e-4d5d47517f6f'), 'eaa65ab279d0d28d43f4b6db9838ba5ab07bbf787aaee3557707f0aa0c2395e1', UUID('7b8690ea-4bcd-453d-a545-ae7d2aa17026'), None, datetime.datetime(2026, 11, 15, 14, 12, 44, 348504), None, None)]
E   (Background on this error at: https://sqlalche.me/e/21/gkpj)
=========================================================================================================== tests coverage =========================================================================================================== 
__________________________________________________________________________________________ coverage: platform win32, python 3.12.11-final-0 __________________________________________________________________________________________ 

Name                                                 Stmts   Miss  Cover   Missing
----------------------------------------------------------------------------------
apps\api\src\app\__init__.py                             1      0   100%
apps\api\src\app\agent\__init__.py                       0      0   100%
apps\api\src\app\agent\context_builder.py               87     43    51%   70-73, 86-231, 237-256
apps\api\src\app\agent\limits.py                        59     40    32%   32-43, 46-47, 53-55, 58-59, 65, 68-70, 76, 81-90, 95-100, 109-111, 133-147
apps\api\src\app\agent\orchestrator.py                 167    137    18%   53-54, 58-59, 66-71, 79-110, 122-143, 152-185, 189-258, 270-306, 315-337, 345-447, 461-469, 474-485
apps\api\src\app\agent\output_validation.py             51     34    33%   29-39, 49-55, 60, 70-72, 76, 82-99
apps\api\src\app\agent\schemas.py                       94      0   100%
apps\api\src\app\agent\tools.py                         46     30    35%   28-30, 33-34, 38-71, 75-79, 91-101, 105-115, 122-126
apps\api\src\app\api\__init__.py                         0      0   100%
apps\api\src\app\api\errors.py                          49     21    57%   74-78, 104-105, 110-115, 126-139
apps\api\src\app\api\middleware.py                      38      5    87%   43, 48, 58, 66, 75
apps\api\src\app\api\router.py                          39      2    95%   59, 68
apps\api\src\app\backup\__init__.py                      0      0   100%
apps\api\src\app\backup\encryption.py                   19     19     0%   9-40
apps\api\src\app\backup\manifest.py                     37     37     0%   10-90
apps\api\src\app\backup\restore.py                      82     82     0%   14-158
apps\api\src\app\backup\retention.py                    44     44     0%   8-72
apps\api\src\app\backup\snapshot.py                    104    104     0%   13-217
apps\api\src\app\cli.py                                158    158     0%   11-255
apps\api\src\app\config.py                             120     24    80%   152, 161, 169-194, 197
apps\api\src\app\db\__init__.py                          0      0   100%
apps\api\src\app\db\base.py                              4      0   100%
apps\api\src\app\db\models\__init__.py                   8      0   100%
apps\api\src\app\db\models\auth.py                      59      0   100%
apps\api\src\app\db\models\catalog.py                   72      0   100%
apps\api\src\app\db\models\knowledge.py                 64      0   100%
apps\api\src\app\db\models\memory.py                     1      1     0%   9
apps\api\src\app\db\models\nutrition.py                 34      0   100%
apps\api\src\app\db\models\operations.py               113      0   100%
apps\api\src\app\db\models\profile.py                   60      0   100%
apps\api\src\app\db\models\training.py                  65      0   100%
apps\api\src\app\db\session.py                          15      8    47%   34-42
apps\api\src\app\jobs\__init__.py                        0      0   100%
apps\api\src\app\jobs\handlers\__init__.py              11     11     0%   5-27
apps\api\src\app\jobs\handlers\delete_user.py           14     14     0%   8-26
apps\api\src\app\jobs\handlers\export_user.py           44     44     0%   8-98
apps\api\src\app\jobs\handlers\generate_plan.py         57     57     0%   8-131
apps\api\src\app\jobs\handlers\import_knowledge.py     137    137     0%   13-230
apps\api\src\app\jobs\handlers\knowledge_index.py       30     30     0%   8-52
apps\api\src\app\jobs\handlers\maintenance.py           34     34     0%   10-68
apps\api\src\app\jobs\handlers\weekly_review.py         19     19     0%   8-34
apps\api\src\app\jobs\queue.py                         117     95    19%   34-58, 68-97, 102-118, 123-129, 133-144, 156-173, 185-196, 201-217, 222-233, 238-243, 248-258, 262-266
apps\api\src\app\jobs\scheduler.py                      55     55     0%   11-103
apps\api\src\app\jobs\worker.py                        104    104     0%   12-153
apps\api\src\app\main.py                                43     12    72%   35-40, 78, 84-92, 107
apps\api\src\app\media\__init__.py                       0      0   100%
apps\api\src\app\media\audio_extract.py                 63     63     0%   11-131
apps\api\src\app\media\subtitles.py                     69     69     0%   9-105
apps\api\src\app\media\validation.py                    45     29    36%   28-43, 48-53, 58-64
apps\api\src\app\modules\__init__.py                     0      0   100%
apps\api\src\app\modules\auth\__init__.py                0      0   100%
apps\api\src\app\modules\auth\dependencies.py           48     28    42%   27-30, 35-36, 48, 65-91, 98-109, 115-120
apps\api\src\app\modules\auth\router.py                 68     39    43%   48-54, 68-86, 99, 113-116, 127-134, 143-148, 158-160, 172-174
apps\api\src\app\modules\auth\schemas.py                74      9    88%   29, 84-87, 98-101
apps\api\src\app\modules\auth\service.py               126     91    28%   58-69, 72-73, 92, 96-106, 109-110, 118-127, 135, 139, 143, 146-179, 185-204, 208-214, 217-218, 224-239, 247-264, 268-295
apps\api\src\app\modules\catalog\__init__.py             4      0   100%
apps\api\src\app\modules\catalog\admin_router.py        55     29    47%   40-43, 54-56, 65-70, 79-81, 90-92, 103-107, 124-128
apps\api\src\app\modules\catalog\router.py              17      6    65%   26-28, 38-40
apps\api\src\app\modules\catalog\schemas.py             63      0   100%
apps\api\src\app\modules\catalog\service.py            191    158    17%   49, 53, 58-97, 102-130, 137, 147-156, 159, 162-169, 179-226, 232-275, 278-305, 308-340, 349-357, 362-370, 373-378, 381-403, 414-415
apps\api\src\app\modules\conversations\__init__.py       0      0   100%
apps\api\src\app\modules\conversations\router.py        71     46    35%   41-71, 92-98, 108-119, 128-134, 146-162, 174-180
apps\api\src\app\modules\conversations\schemas.py       42      0   100%
apps\api\src\app\modules\deletion\__init__.py            0      0   100%
apps\api\src\app\modules\deletion\ledger.py             68     54    21%   33-41, 46-100, 105-118, 123
apps\api\src\app\modules\deletion\router.py             22     11    50%   32-51
apps\api\src\app\modules\exports\__init__.py             0      0   100%
apps\api\src\app\modules\exports\router.py              20      8    60%   27-34, 44-51
apps\api\src\app\modules\exports\schemas.py             12      0   100%
apps\api\src\app\modules\knowledge\permissions.py       24     15    38%   21-25, 32-35, 40-43, 48-54
apps\api\src\app\modules\knowledge\router.py            61     34    44%   51-55, 70-72, 92-100, 111-113, 126-129, 144-156, 166-168, 179-181, 191-195
apps\api\src\app\modules\knowledge\schemas.py           74      0   100%
apps\api\src\app\modules\knowledge\service.py          132    109    17%   34-35, 43-81, 93-114, 130-170, 178-193, 196-218, 228-254, 258-279, 283-290, 294-301
apps\api\src\app\modules\measurements\__init__.py        0      0   100%
apps\api\src\app\modules\measurements\router.py         23     13    43%   28-49
apps\api\src\app\modules\measurements\schemas.py        20      0   100%
apps\api\src\app\modules\nutrition\__init__.py           0      0   100%
apps\api\src\app\modules\nutrition\router.py            41     26    37%   34-51, 65-84
apps\api\src\app\modules\nutrition\schemas.py           27      0   100%
apps\api\src\app\modules\plans\diff.py                  36     34     6%   14-74
apps\api\src\app\modules\plans\router.py                41     23    44%   34-36, 49-51, 64-78, 88-96, 111-117
apps\api\src\app\modules\plans\schemas.py               96     16    83%   48-59, 94-97
apps\api\src\app\modules\plans\service.py              118     97    18%   29, 36-41, 44-47, 52-68, 72-97, 117-155, 158-161, 176-236
apps\api\src\app\modules\plans\validators.py            88     80     9%   28-240
apps\api\src\app\modules\profiles\__init__.py            0      0   100%
apps\api\src\app\modules\profiles\router.py             51     26    49%   34-40, 54-56, 65-66, 74-76, 86-88, 99-103, 113-115, 126-130
apps\api\src\app\modules\profiles\schemas.py            85     13    85%   65-77
apps\api\src\app\modules\profiles\service.py           112     92    18%   25, 32-33, 36-41, 45-75, 79-88, 95-101, 111-146, 152-185, 192-198, 210-221, 227-265
apps\api\src\app\modules\reviews\__init__.py             0      0   100%
apps\api\src\app\modules\reviews\builder.py             40     28    30%   23-24, 29-103, 124-126, 131
apps\api\src\app\modules\reviews\router.py              31     14    55%   30-32, 40-42, 53-57, 67-69
apps\api\src\app\modules\reviews\schemas.py             21      0   100%
apps\api\src\app\modules\reviews\service.py             78     54    31%   39-40, 44-62, 66-97, 101-142, 145-151, 154-157, 161-171
apps\api\src\app\modules\sync\__init__.py                0      0   100%
apps\api\src\app\modules\sync\router.py                 26     11    58%   38-51, 60-62
apps\api\src\app\modules\sync\schemas.py               115      0   100%
apps\api\src\app\modules\sync\service.py               157    130    17%   54-55, 62, 69-83, 87-147, 154-159, 171-182, 194-318, 326-446
apps\api\src\app\modules\workouts\__init__.py            0      0   100%
apps\api\src\app\modules\workouts\router.py             48     25    48%   39-43, 55-57, 67-75, 90-99, 108-110, 121-134, 145-147
apps\api\src\app\modules\workouts\schemas.py           106      3    97%   139-141
apps\api\src\app\modules\workouts\service.py           193    167    13%   27-37, 44, 61-81, 84-87, 98-116, 120-127, 138-155, 168-208, 227-251, 256-259, 262-268, 292-339, 342-345, 348-355, 372-412, 416-437, 445-460, 464-472        
apps\api\src\app\modules\workouts\statistics.py         84     51    39%   39-55, 70, 74, 81-111, 126-144, 154-160
apps\api\src\app\providers\__init__.py                  28     18    36%   16-21, 26-31, 36-41, 46-48
apps\api\src\app\providers\errors.py                    33     18    45%   13-16, 21, 26, 31, 36, 41, 49, 54-61
apps\api\src\app\providers\fake.py                      71     38    46%   47-60, 79-81, 87-98, 115-125, 128-134, 141-144
apps\api\src\app\providers\interfaces.py                51      0   100%
apps\api\src\app\providers\paraformer.py                90     90     0%   9-158
apps\api\src\app\providers\qwen_chat.py                 50     38    24%   27-30, 33-76, 94-100
apps\api\src\app\providers\qwen_embedding.py            36     36     0%   8-72
apps\api\src\app\rag\__init__.py                         0      0   100%
apps\api\src\app\rag\chunking.py                        79     79     0%   10-140
apps\api\src\app\rag\citations.py                       58     45    22%   31-40, 50-98, 102
apps\api\src\app\rag\fusion.py                          44     44     0%   8-88
apps\api\src\app\rag\indexing.py                        46     46     0%   10-120
apps\api\src\app\rag\normalization.py                   29     29     0%   8-81
apps\api\src\app\rag\retrieval.py                       96     96     0%   12-230
apps\api\src\app\services\__init__.py                    0      0   100%
apps\api\src\app\services\capabilities.py               28     20    29%   16-18, 26-29, 39-51, 56-60
apps\api\src\app\services\planning.py                   31     23    26%   23-29, 34-37, 42-47, 60-69
apps\api\src\app\storage\__init__.py                     4      2    50%   10-12
apps\api\src\app\storage\filesystem.py                  46     46     0%   8-98
apps\api\src\app\storage\interfaces.py                  16      0   100%
apps\api\src\app\storage\oss.py                         81     81     0%   9-163
apps\api\src\app\utils\__init__.py                       0      0   100%
apps\api\src\app\utils\auth.py                          26      8    69%   19, 29, 34, 44, 49-50, 61-62
apps\api\src\app\utils\password.py                      13      6    54%   42-46, 59
apps\api\src\app\utils\validation.py                    29     10    66%   19, 22, 25, 32, 48, 51, 54, 70, 73, 76
----------------------------------------------------------------------------------
TOTAL                                                 6326   3875    39%
Coverage HTML written to dir htmlcov
====================================================================================================== short test summary info ======================================================================================================= 
FAILED apps\api\tests\integration\test_auth_and_csrf.py::test_register_login_logout_flow - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_auth_and_csrf.py::test_write_without_csrf_rejected - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_auth_and_csrf.py::test_login_wrong_password_uniform_error - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_auth_and_csrf.py::test_cross_user_access_returns_404 - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_plan_activation_conflict.py::test_stale_basis_rejects_activation - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_plan_activation_conflict.py::test_activation_supersedes_previous_active - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_record_version_conflict.py::test_wrong_expected_version_conflicts - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_record_version_conflict.py::test_correct_version_updates_and_records_revision - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_sync_idempotency.py::test_replay_same_event_returns_already_applied - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_sync_idempotency.py::test_same_id_different_content_conflicts - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_sync_idempotency.py::test_set_without_parent_is_dependency_pending - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
FAILED apps\api\tests\integration\test_sync_partial_failure.py::test_failed_middle_event_keeps_first_and_third - sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.ForeignKeyViolationError) insert or update on table "invites" violates foreign key constraint "invites_created_by_fkey"
12 failed, 2 passed in 16.49s