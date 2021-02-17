<?php
session_start();
unset($_SESSION["errormessage"]);
if($_SERVER["REQUEST_METHOD"] == "POST") {
    $servername = "localhost";
    $username = real_input($_POST["username"]);
    $password = real_input($_POST["password"]);
    if(!empty($username) and !empty($password)) {
        $conn = new mysqli($servername, $username, $password);
        if ($conn->connect_error) {
            $_SESSION["errormessage"] = "Connection fail!";
            header('Location: login.php');
            exit;
        } else {
            $_SESSION["loggedin"] = true;
            $_SESSION["servername"] = $servername;
            $_SESSION["username"] = $username;
            $_SESSION["password"] = $password;
            header('Location: welcome.php');
            exit;
        }
    } else {
        header('Location: login.php');
        exit;
    }
} else {
    header('Location: login.php');
    exit;
}


function real_input($data)
{
    $data = trim($data);
    $data = stripslashes($data);
    $data = htmlspecialchars($data);
    return $data;
}
?>
