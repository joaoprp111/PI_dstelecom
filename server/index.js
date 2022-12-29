const express = require("express");
const axios = require("axios");
const app = express();
const cors = require("cors");
const pool = require("./db");

//middleware
//app.use(cors());
app.use(cors({ withCredentials: true }));
app.use(express.json()); //req.body
app.use(express.urlencoded({ extended: false }));


function generateToken() {
	const crypto = require('crypto');
	return crypto.randomBytes(64).toString('hex');
}

app.post("/login", async (req, res) => {
	console.log(req.body)
	const { username, password } = req.body
	try {
		pool.connect();
		const allTodos = await pool.query("SELECT * FROM equipas where id='" + username + "';");
		if (allTodos.rows.length > 0) {
			if (password == allTodos.rows[0].password) {
				token = generateToken();
				res.json({ token });
				console.log(token)
			}
		}
		else {
			res.status(401).json({ error: 'Invalid username or password' });
		}
	} catch (err) {
		console.error(err.message);
	}

});

app.get("/todos", async (req, res) => {
	console.log('request')
	try {
		pool.connect();
		const allTodos = await pool.query("SELECT * FROM equipas");
		res.json(allTodos.rows);
	} catch (err) {
		console.error(err.message);
	}
});

app.get('/equipa/delete/:id', async(req,res) => {
	console.log("Estou cá!")
	const id = req.params.id
	axios.delete('http://localhost:3001/equipa/delete/' + id)
		.then(dados => {res.redirect('/equipa')})
		.catch(err => console.log(err))
})

app.get('/equipa/:id', async (req, res) => {
	const id = req.params.id
	try {
		pool.connect();
		const equipa = await pool.query("SELECT * FROM skill where id_equipa='" + id + "';");
		res.json(equipa.rows);
	}
	catch (err) {
		console.log(err.message)
	}
});



// catch 404 and forward to error handler
app.use(function (req, res, next) {
	next(createError(404));
});

// error handler
app.use(function (err, req, res, next) {
	// set locals, only providing error in development
	res.locals.message = err.message;
	res.locals.error = req.app.get("env") === "development" ? err : {};

	// render the error page
	res.status(err.status || 500);
	res.json({ error: err });
});

module.exports = app;
