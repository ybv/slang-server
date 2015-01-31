CREATE TABLE users(
 id serial PRIMARY KEY,
 fullname varchar(50),
 email varchar(50) UNIQUE NOT NULL,
 password varchar(50) NOT NULL,
 karma bigint default 0,
 created_at timestamp with time zone default current_timestamp
);

